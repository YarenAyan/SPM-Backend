# sis/models.py
from django.db import models
# Django'nun User modelini kullanmak yerine özel bir model oluşturmak daha iyi olabilir,
# ancak şimdilik SQL'deki gibi alanları olan bir yapı varsayalım veya
# Django'nun User modelini kullanıp Profile modeli ile genişletelim.
# **ÖNEMLİ:** Eğer Django'nun User modelini kullanıyorsanız, 'role', 'student_id',
# 'employee_id' gibi alanlar doğrudan orada olmaz. Bunları bir Profile
# modeli ile (OneToOneField) bağlamak gerekir. Aşağıdaki kod, bu alanların
# doğrudan User modelinde olduğunu varsayar, bu kısmı kendi User model
# yapınıza göre uyarlamanız GEREKEBİLİR.
from django.contrib.auth.models import AbstractUser # Veya AbstractBaseUser

# Eğer özel User modeli kullanacaksanız:
# class User(AbstractUser): # Veya AbstractBaseUser ve PermissionsMixin
#     ROLE_CHOICES = [('student', 'Student'), ('instructor', 'Instructor'), ('secretary', 'Secretary')]
#     role = models.CharField(max_length=10, choices=ROLE_CHOICES, null=False, blank=False)
#     student_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
#     employee_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
#     birth_date = models.DateField(null=True, blank=True)
#     department = models.CharField(max_length=100, null=True, blank=True)
#     office_location = models.CharField(max_length=100, null=True, blank=True)
#     # email, first_name, last_name, password AbstractUser'dan gelir.
#     # password_hash SQL'deki alana karşılık Django'nun password alanı kullanılır.
#     # created_at, updated_at AbstractUser'da yoktur, eklenebilir:
#     # created_at = models.DateTimeField(auto_now_add=True)
#     # updated_at = models.DateTimeField(auto_now=True)

#     # USERNAME_FIELD = 'email' # Email ile giriş için
#     # REQUIRED_FIELDS = ['first_name', 'last_name'] # Createsuperuser için

#     def __str__(self):
#         return self.email


# Şimdilik Django'nun standart User modelini kullanıp, eksik alanları
# Profile modelinde tuttuğumuzu varsayalım (daha yaygın yöntem):
from django.conf import settings
from django.contrib.auth.models import User as DjangoUser # Django User'ı farklı isimle alalım

class UserProfile(models.Model):
    """Django User modelini genişleten profil modeli"""
    ROLE_CHOICES = [('student', 'Student'), ('instructor', 'Instructor'), ('secretary', 'Secretary')]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, null=False, blank=False)
    student_id_profile = models.CharField(max_length=20, unique=True, null=True, blank=True) # SQL'deki student_id
    employee_id_profile = models.CharField(max_length=20, unique=True, null=True, blank=True) # SQL'deki employee_id
    birth_date = models.DateField(null=True, blank=True)
    department = models.CharField(max_length=100, null=True, blank=True)
    office_location = models.CharField(max_length=100, null=True, blank=True)
    # created_at, updated_at gerekirse eklenebilir

    def __str__(self):
        return f"{self.user.username}'s Profile ({self.get_role_display()})"

# Course modeli
class Course(models.Model):
    course_id = models.AutoField(primary_key=True)
    course_code = models.CharField(max_length=10, unique=True, null=True, blank=True) # SQL'de UNIQUE ama NULL olabilir mi? Gerekirse null=False yap.
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    # instructor_id SQL'deki FK'yı temsil eder. Django User modeline bağlanır.
    # Dikkat: SQL'deki instructor_id INT ama INSERT'lerde employee_id kullanılmış gibi.
    # Doğrusu User'ın PK'sına (user_id) bağlanmaktır.
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='taught_courses') # limit_choices_to={'profile__role': 'instructor'} eklenebilir
    grading_details = models.JSONField(null=True, blank=True) # MySQL 5.7+ JSONField destekler
    office_hours = models.TextField(null=True, blank=True) # SQL'deki TEXT
    image_url = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.course_code or 'NOCODE'} - {self.title}"

# Enrollment modeli
class Enrollment(models.Model):
    enrollment_id = models.AutoField(primary_key=True)
    # Dikkat: SQL'de student_id VARCHAR(20) ve INT FK olarak karışık kullanılmış.
    # Mantıken Users tablosunun PK'sı olan user_id'ye (INT) bağlanmalı.
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='enrollments') # limit_choices_to={'profile__role': 'student'} eklenebilir
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='students_enrolled') # related_name değişti
    enrollment_date = models.DateField(null=True, blank=True) # SQL'de NULL olabilir
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # SQL'deki UNIQUE KEY unique_enrollment (student_id, course_id) karşılığı
        unique_together = ('student', 'course')

    def __str__(self):
        return f"{self.student.username} enrolled in {self.course.title}"

# Exam modeli
class Exam(models.Model):
    EXAM_TYPE_CHOICES = [
        ('Midterm', 'Midterm'), ('Final', 'Final'), ('Resit', 'Resit'),
        ('Research', 'Research'), ('Quiz', 'Quiz') # SQL'deki ENUM değerleri
    ]
    STATUS_CHOICES = [
        ('Scheduled', 'Scheduled'), ('Not Graded', 'Not Graded'),
        ('Graded', 'Graded'), ('Cancelled', 'Cancelled') # SQL'deki ENUM değerleri
    ]
    exam_id = models.AutoField(primary_key=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='exams')
    exam_type = models.CharField(max_length=10, choices=EXAM_TYPE_CHOICES, null=False, blank=False) # SQL'de NOT NULL
    exam_name = models.CharField(max_length=255, null=True, blank=True) # SQL'de NULL olabilir
    exam_datetime = models.DateTimeField(null=True, blank=True, db_column='exam_date') # SQL'deki exam_date (DATETIME)
    location = models.CharField(max_length=100, null=True, blank=True) # SQL'deki location VARCHAR(100)
    details = models.TextField(null=True, blank=True) # SQL'deki details TEXT
    rules = models.TextField(null=True, blank=True) # SQL'deki rules TEXT
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Scheduled') # SQL'deki status ENUM
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        dt_str = self.exam_datetime.strftime('%Y-%m-%d %H:%M') if self.exam_datetime else "No Date"
        return f"{self.course.course_code} - {self.get_exam_type_display()} ({dt_str})"

# Grade modeli
class Grade(models.Model):
    LETTER_GRADE_CHOICES = [
        ('AA', 'AA'), ('BA', 'BA'), ('BB', 'BB'), ('CB', 'CB'), ('CC', 'CC'),
        ('DC', 'DC'), ('DD', 'DD'), ('FD', 'FD'), ('FF', 'FF'),
        ('DZ', 'DZ'), # SQL'deki ENUM değerleri
        # ('PENDING', 'Pending') # API'de not yoksa PENDING gibi bir durum yönetilebilir
    ]
    RESIT_STATUS_CHOICES = [
        ('None', 'None'), ('Requested', 'Requested'),
        ('Approved', 'Approved'), ('Denied', 'Denied') # SQL'deki ENUM değerleri
    ]
    grade_id = models.AutoField(primary_key=True)
    # Dikkat: Yine student_id (Users PK'sına INT FK olmalı)
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='grades') # limit_choices_to={'profile__role': 'student'}
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='grades')
    letter_grade = models.CharField(max_length=2, choices=LETTER_GRADE_CHOICES, null=False, blank=False) # SQL'de NOT NULL
    numeric_grade = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True) # SQL'deki DECIMAL(5, 2)
    is_resit_eligible = models.BooleanField(default=False) # SQL'deki BOOLEAN
    resit_request_status = models.CharField(max_length=10, choices=RESIT_STATUS_CHOICES, default='None') # SQL'deki ENUM
    graded_at = models.DateTimeField(null=True, blank=True) # SQL'deki DATETIME
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # SQL'deki UNIQUE KEY unique_grade (student_id, exam_id)
        unique_together = ('student', 'exam')

    def __str__(self):
        return f"{self.student.username} - {self.exam} - Grade: {self.get_letter_grade_display()}"

    def save(self, *args, **kwargs):
        # Resit uygunluğunu SQL'deki boolean alana göre ayarla (basit mantık)
        eligible_grades = ['FF', 'FD', 'DD', 'DC']
        if self.letter_grade in eligible_grades and self.letter_grade != 'DZ':
            self.is_resit_eligible = True
        else:
            self.is_resit_eligible = False
        # Eğer talep durumu 'None' değilse, uygunluk durumu değişmemeli (opsiyonel kural)
        # existing_status = Grade.objects.get(pk=self.pk).resit_request_status if self.pk else 'None'
        # if existing_status != 'None':
        #     self.is_resit_eligible = Grade.objects.get(pk=self.pk).is_resit_eligible

        super().save(*args, **kwargs) # Asıl kaydetme

# Announcement modeli
class Announcement(models.Model):
    announcement_id = models.AutoField(primary_key=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='announcements')
    # Dikkat: instructor_id (Users PK'sına INT FK olmalı)
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posted_announcements') # limit_choices_to={'profile__role': 'instructor'}
    title = models.CharField(max_length=255)
    message = models.TextField(null=True, blank=True) # SQL'de TEXT (NOT NULL değil)
    file_attachment_url = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True) # SQL'de NULL olabilir, elle girilebilir veya auto_now_add=True
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Announcement for {self.course.course_code}: {self.title}"