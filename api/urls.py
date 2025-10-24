from django.urls import path
from user.views import RegisterView, LoginView, ProfileView, ChangePasswordView ,  ForgotPasswordView, ResetPasswordView ,  CreateOrderView, VerifyPaymentView 
from order.views import DummyPaymentView , UserOrdersView
# website/urls.py
from django.urls import path
from website.views import (
    WebsiteRequestCreateView,
    WebsiteRequestListView,
    WebsiteRequestDetailView,
    WebsiteRequestUserUpdateView,
    AdminWebsiteRequestUpdateView
)
from template.views import TemplateListView
from chat.views import MessageHistoryView, UnreadCountView
from message.views import ContactMessageCreateView
urlpatterns = [
    path('signup/', RegisterView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
     path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/<uidb64>/<token>/', ResetPasswordView.as_view(), name='reset-password'),
     path('create-order/', CreateOrderView.as_view(), name='create-order'),
    path('verify-payment/', VerifyPaymentView.as_view(), name='verify-payment'),
    path("dummy-payment/", DummyPaymentView.as_view(), name="dummy-payment"),
    path('requests/create/', WebsiteRequestCreateView.as_view(), name='request-create'),
    path('requests/list/', WebsiteRequestListView.as_view(), name='request-list'),
    path('requests/list/<int:id>/', WebsiteRequestDetailView.as_view(), name='request-detail'),
    path('requests/list/<int:id>/update/', WebsiteRequestUserUpdateView.as_view(), name='request-user-update'),
    path('admin/requests/<int:id>/update/', AdminWebsiteRequestUpdateView.as_view(), name='request-admin-update'),
    path("orders/", UserOrdersView.as_view(), name="user-orders"),
    path('templates/', TemplateListView.as_view(), name='template-list'),
  path('messages/<str:email>/', MessageHistoryView.as_view(), name='message-history'),
    path('unread-count/', UnreadCountView.as_view(), name='unread-count'),
    path('contact-message/',ContactMessageCreateView.as_view(),name='contact-message'),
]

