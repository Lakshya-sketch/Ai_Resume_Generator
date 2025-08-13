# core/forms.py
from django import forms

class ResumeForm(forms.Form):
    prompt = forms.CharField(widget=forms.Textarea, label="Your Prompt")
    resume_pdf = forms.FileField(label="Upload Your Resume (PDF)")
