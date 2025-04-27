from rest_framework import serializers
from .models import Course, Enrollment, Exam, Grade, Announcement, UserProfile # Profile modelini import et
from django.contrib.auth.models import User # Django'nun User modeli

# === Temel Serializer'lar ===

class UserBasicSerializer(serializers.ModelSerializer):
    """Sadece ad-soyad göstermek için"""
    class Meta:
        model = User # Django User modeli
        fields = ['id', 'first_name', 'last_name', 'email']

class UserProfileSerializer(serializers.ModelSerializer):
    """Kullanıcı profil bilgilerini göstermek için"""
    user = UserBasicSerializer(read_only=True) # İç içe User bilgisi

    class Meta:
        model = UserProfile
        fields = [
            'user', # User bilgileri
            'role',
            'student_id_profile', # Modeldeki adı kullandık
            'employee_id_profile',# Modeldeki adı kullandık
            'birth_date',
            'department',
            'office_location',
        ]

# === Öğrenci API'leri için Serializer'lar ===

class StudentDashboardCourseSerializer(serializers.ModelSerializer):
    """Öğrenci dashboard'ı için ders bilgileri."""
    instructor_name = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'course_id',
            'title',
            'instructor_name',
            'image_url',
            'course_code', # Frontend isteyebilir
        ]
        read_only_fields = fields # Sadece okuma

    def get_instructor_name(self, obj):
        if obj.instructor:
            # Django User modelinin ad/soyadını alalım
            return f"{obj.instructor.first_name} {obj.instructor.last_name}"
        return "N/A"


class AnnouncementSerializer(serializers.ModelSerializer):
    """Ders duyuruları"""
    instructor_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Announcement
        # file_attachment_url SQL'de var, ekleyelim
        fields = ['announcement_id', 'title', 'message', 'created_at', 'instructor_name', 'file_attachment_url']
        read_only_fields = ['announcement_id', 'created_at', 'instructor_name']

    def get_instructor_name(self, obj):
        if obj.instructor:
            return f"{obj.instructor.first_name} {obj.instructor.last_name}"
        return "N/A"

class CourseDetailSerializer(serializers.ModelSerializer):
    """Bir dersin tüm detayları (öğrenci görünümü)"""
    # instructor ilişkisi Django User modeline, basic serializer ile gösterelim
    instructor = UserBasicSerializer(read_only=True)
    # İlişkili duyuruları da getirelim (related_name='announcements' kullanılır)
    announcements = AnnouncementSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = [
            'course_id', 'course_code', 'title', 'description',
            'instructor', 'grading_details', 'office_hours',
            'announcements', # İç içe duyurular
        ]


class CourseBasicSerializer(serializers.ModelSerializer):
    """Sadece ID, kod ve başlık"""
    class Meta:
        model = Course
        fields = ['course_id', 'course_code', 'title']

class ExamBasicSerializer(serializers.ModelSerializer):
    """Not listesinde sınavın temel bilgilerini göstermek için"""
    course = CourseBasicSerializer(read_only=True)
    # exam_type için choices'dan gelen okunabilir değeri al
    exam_type_display = serializers.CharField(source='get_exam_type_display', read_only=True)

    class Meta:
        model = Exam
        fields = ['exam_id', 'course', 'exam_type_display', 'exam_name', 'exam_datetime']


class GradeSerializer(serializers.ModelSerializer):
    """Öğrencinin bir dersteki notlarını listelemek için"""
    exam = ExamBasicSerializer(read_only=True) # Sınavın temel bilgileri
    # letter_grade için okunabilir değer (DZ durumunda önemli olabilir)
    letter_grade_display = serializers.CharField(source='get_letter_grade_display', read_only=True)
    # Resit talep durumunun okunabilir hali
    resit_status_display = serializers.CharField(source='get_resit_request_status_display', read_only=True)

    class Meta:
        model = Grade
        fields = [
            'grade_id',
            'exam',
            'letter_grade',
            'letter_grade_display',
            'numeric_grade',
            'is_resit_eligible',    # SQL'deki boolean alan
            'resit_request_status', # SQL'deki enum alan
            'resit_status_display', # Okunabilir talep durumu
            'graded_at',
        ]
        read_only_fields = fields # Öğrenci notunu API üzerinden değiştiremez

class StudentExamSerializer(serializers.ModelSerializer):
    """Öğrencinin sınav takvimi için"""
    course = CourseBasicSerializer(read_only=True)
    exam_type_display = serializers.CharField(source='get_exam_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    student_grade = serializers.SerializerMethodField() # Notu ekle

    class Meta:
        model = Exam
        fields = [
            'exam_id', 'course', 'exam_type_display', 'exam_name',
            'exam_datetime', 'location', 'status', 'status_display',
            'student_grade'
        ]

    def get_student_grade(self, obj):
        student = self.context.get('student')
        if student:
            try:
                # exam_id ve student user_id ile notu bul
                grade = Grade.objects.get(exam=obj, student=student)
                # Sadece harf notunu döndür (veya GradeSerializer kullan)
                return grade.letter_grade
            except Grade.DoesNotExist:
                # Eğer sınavın durumu 'Graded' ise ama not yoksa belki 'N/A'
                # return 'N/A' if obj.status == 'Graded' else 'Pending'
                return None # Henüz not yok
        return None

class ExamDetailSerializer(serializers.ModelSerializer):
    """Bir sınavın tüm detayları (öğrenci görünümü)"""
    course = CourseBasicSerializer(read_only=True)
    exam_type_display = serializers.CharField(source='get_exam_type_display', read_only=True)
    student_grade_info = serializers.SerializerMethodField() # Öğrencinin not detayları

    class Meta:
        model = Exam
        fields = [
            'exam_id', 'course', 'exam_type_display', 'exam_name',
            'exam_datetime', 'location', 'details', 'rules',
            'student_grade_info',
        ]

    def get_student_grade_info(self, obj):
        student = self.context.get('student')
        if student:
            try:
                grade = Grade.objects.get(exam=obj, student=student)
                # Notun tüm detaylarını GradeSerializer ile döndür
                return GradeSerializer(grade).data
            except Grade.DoesNotExist:
                return None
        return None

class ResitEligibilitySerializer(serializers.Serializer):
    """Bütünleme uygunluk kontrolü için özel serializer"""
    eligible = serializers.BooleanField()
    message = serializers.CharField()
    resit_request_status = serializers.CharField()
    letter_grade = serializers.CharField() # Notu da döndürelim