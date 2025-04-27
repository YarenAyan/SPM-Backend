from django.urls import path
from . import views

urlpatterns = [
    path('student/dashboard/', views.StudentDashboardView.as_view(), name='student-dashboard'),
    path('student/grades/course/<int:course_pk>/', views.StudentCourseGradesView.as_view(), name='student-course-grades'),
    path('student/exams/', views.StudentExamsView.as_view(), name='student-exams'),
    path('student/grades/<int:grade_pk>/check-resit/', views.CheckResitEligibilityView.as_view(), name='check-resit'),
    path('student/grades/<int:grade_pk>/request-resit/', views.RequestResitExamView.as_view(), name='request-resit'),
    path('courses/search/', views.CourseSearchView.as_view(), name='course-search'),
    path('courses/<int:pk>/', views.CourseDetailView.as_view(), name='course-detail'),
    path('exams/<int:pk>/', views.ExamDetailView.as_view(), name='exam-detail'),
]