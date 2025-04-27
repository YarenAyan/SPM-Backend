from rest_framework import generics, permissions, views, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q # Arama için
from django.contrib.auth.models import User # Django User

from .models import Course, Enrollment, Exam, Grade, Announcement # Güncel modeller
from .serializers import ( # Güncel serializerlar
    StudentDashboardCourseSerializer, CourseSerializer, CourseDetailSerializer,
    GradeSerializer, StudentExamSerializer, ExamDetailSerializer,
    CourseBasicSerializer, ResitEligibilitySerializer
)

# === İzin Sınıfları (Yetkilendirme) ===
# Bu sınıflar UserProfile modelini varsayıyor
class IsStudent(permissions.BasePermission):
    def has_permission(self, request, view):
        return (request.user and request.user.is_authenticated and
                hasattr(request.user, 'profile') and request.user.profile.role == 'student')

class IsEnrolledStudent(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated and
                hasattr(request.user, 'profile') and request.user.profile.role == 'student'):
            return False # Önce öğrenci mi kontrol et

        course = None
        if isinstance(obj, Course):
            course = obj
        elif isinstance(obj, Exam):
            course = obj.course
        elif isinstance(obj, Grade):
             # Notun sahibi istek atan kullanıcı mı?
            return obj.student == request.user
        else:
            return False

        if course:
            # Kullanıcı derse kayıtlı mı?
            return Enrollment.objects.filter(student=request.user, course=course).exists()
        return False


# === Öğrenci API View'ları ===

class StudentDashboardView(generics.ListAPIView):
    """Giriş yapmış öğrencinin kayıtlı olduğu dersleri listeler."""
    serializer_class = StudentDashboardCourseSerializer
    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def get_queryset(self):
        student = self.request.user
        # Öğrencinin kayıtlı olduğu dersleri çek
        enrolled_courses_ids = Enrollment.objects.filter(student=student).values_list('course_id', flat=True)
        # select_related ile instructor bilgisini tek sorguda çek
        return Course.objects.filter(course_id__in=enrolled_courses_ids).select_related('instructor')

class CourseSearchView(generics.ListAPIView):
    """Tüm dersleri listeler ve arama (filtreleme) sağlar."""
    serializer_class = CourseBasicSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Course.objects.all().select_related('instructor')
        search_term = self.request.query_params.get('search', None)
        if search_term:
            queryset = queryset.filter(
                Q(title__icontains=search_term) |
                Q(instructor__first_name__icontains=search_term) |
                Q(instructor__last_name__icontains=search_term) |
                Q(course_code__icontains=search_term)
            )
        return queryset

class CourseDetailView(generics.RetrieveAPIView):
    """Bir dersin detaylarını (içerik, duyurular) getirir."""
    # prefetch_related ile ilişkili duyuruları ve eğitmenlerini optimize çek
    queryset = Course.objects.prefetch_related('announcements__instructor').select_related('instructor')
    serializer_class = CourseDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsEnrolledStudent]
    lookup_field = 'pk' # course_id

class StudentCourseGradesView(generics.ListAPIView):
    """Bir öğrencinin belirli bir dersteki tüm notlarını listeler."""
    serializer_class = GradeSerializer
    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def get_queryset(self):
        student = self.request.user
        course_pk = self.kwargs.get('course_pk')
        # Hata kontrolü: Ders var mı ve öğrenci kayıtlı mı?
        course = get_object_or_404(Course, pk=course_pk)
        if not Enrollment.objects.filter(student=student, course=course).exists():
             # Öğrenci bu derse kayıtlı değilse boş liste döndür veya hata ver
             return Grade.objects.none() # Boş QuerySet

        # Öğrencinin bu derse ait sınavlardaki notları
        return Grade.objects.filter(
            student=student,
            exam__course_id=course_pk
        ).select_related('exam__course').order_by('-exam__exam_datetime') # Sınav tarihine göre sırala


class StudentExamsView(generics.ListAPIView):
    """Öğrencinin tüm sınavlarını listeler."""
    serializer_class = StudentExamSerializer
    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def get_queryset(self):
        student = self.request.user
        enrolled_courses_ids = Enrollment.objects.filter(student=student).values_list('course_id', flat=True)
        return Exam.objects.filter(
            course_id__in=enrolled_courses_ids
        ).select_related('course').order_by('-exam_datetime') # En yeniden eskiye sırala

    def get_serializer_context(self):
        # Serializer'a öğrenci bilgisini gönder (notları çekmek için)
        context = super().get_serializer_context()
        context['student'] = self.request.user
        return context

class ExamDetailView(generics.RetrieveAPIView):
    """Bir sınavın detaylarını getirir (Öğrenci görünümü)."""
    queryset = Exam.objects.select_related('course')
    serializer_class = ExamDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsEnrolledStudent]
    lookup_field = 'pk' # exam_id

    def get_serializer_context(self):
        # Sınav notunu göstermek için öğrenci bilgisini gönder
        context = super().get_serializer_context()
        context['student'] = self.request.user
        return context

class CheckResitEligibilityView(views.APIView):
    """Bir notun bütünlemeye uygun olup olmadığını kontrol eder."""
    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def get(self, request, grade_pk):
        grade = get_object_or_404(Grade, pk=grade_pk, student=request.user)

        # Mesajı ve durumu SQL'deki alanlara göre belirle
        eligible = grade.is_resit_eligible
        message = ""
        if grade.letter_grade == 'DZ':
            eligible = False # Devamsız ise uygun değil
            message = "Not eligible for resit exam due to absenteeism (DZ)."
        elif eligible and grade.resit_request_status == 'None':
            message = "Eligible for resit exam. You can submit a request."
        elif eligible and grade.resit_request_status == 'Requested':
             message = "You have already requested a resit exam."
        elif eligible and grade.resit_request_status == 'Approved':
             message = "Your resit exam request has been approved."
        elif eligible and grade.resit_request_status == 'Denied':
             message = "Your resit exam request has been denied."
        elif not eligible:
             message = "Not eligible for resit exam for this grade."
        else: # Diğer durumlar
             message = f"Current resit status: {grade.get_resit_request_status_display()}"


        data = {
            'eligible': eligible, # is_resit_eligible alanına göre
            'message': message,
            'resit_request_status': grade.resit_request_status,
            'letter_grade': grade.letter_grade,
        }
        serializer = ResitEligibilitySerializer(data) # Yanıtı formatlamak için
        return Response(serializer.data)

class RequestResitExamView(views.APIView):
    """Öğrencinin bütünleme sınavı talebini alır."""
    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def post(self, request, grade_pk):
        grade = get_object_or_404(Grade, pk=grade_pk, student=request.user)

        # Sadece is_resit_eligible True ise ve talep durumu 'None' ise talep edilebilir
        if grade.is_resit_eligible and grade.resit_request_status == 'None':
            grade.resit_request_status = 'Requested'
            grade.save()
            return Response({'success': True, 'message': 'Resit exam request submitted successfully.', 'new_status': grade.resit_request_status})
        elif grade.resit_request_status != 'None':
             # Zaten bir talep durumu var (Requested, Approved, Denied)
             return Response({'success': False, 'message': f'Cannot request resit. Current status: {grade.get_resit_request_status_display()}'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # is_resit_eligible False ise
            return Response({'success': False, 'message': 'Not eligible to request a resit exam for this grade.'}, status=status.HTTP_400_BAD_REQUEST)