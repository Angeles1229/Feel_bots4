from django import forms

class LoginForm(forms.Form):
    usuario = forms.CharField(max_length=100)
    contraseña = forms.CharField(widget=forms.PasswordInput())
