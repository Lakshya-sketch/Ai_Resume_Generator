# core/views.py

import os
import requests
import pdfplumber
from django.shortcuts import render
from django.http import HttpResponse

from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter

from .forms import ResumeForm

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY or not OPENAI_API_KEY.strip():
    raise ValueError("Error in Loading OPENAI_API_KEY.env file")

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

def process_resume(request):
    if request.method == 'POST':
        form = ResumeForm(request.POST, request.FILES)
        if form.is_valid():
            prompt_text = form.cleaned_data['prompt']
            resume_file = request.FILES['resume_pdf']

            try:
                with pdfplumber.open(resume_file) as pdf:
                    resume_text = "".join(page.extract_text() or "" for page in pdf.pages)
            except Exception as e:
                return HttpResponse(f"Error reading PDF: {e}", status=500)

            full_prompt = f"Based on the following resume, please {prompt_text}.\n\n--- Resume ---\n{resume_text}"

            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {OPENAI_API_KEY}'
            }
            data = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "Role- You are Senior HR of a company . Job - You are to generate the resume based on user prompt according to their requirements after seeing their attached resume and generate final output in a such a format that a pdf should be generated reasily by pdfreport library dont add any uneccesary into and comments.  Optimised resume tailored to the job description and a brief explanation of changes (keywords, formatting, ATS optimisation)"},
                    {"role": "user", "content": full_prompt}
                ]
            }

            try:
                print(f"🔑 Using API Key ending in: ...{OPENAI_API_KEY[-4:]}")
                api_response = requests.post(OPENAI_API_URL, headers=headers, json=data)
                api_response.raise_for_status()
                response_data = api_response.json()

                if 'error' in response_data:
                    return HttpResponse(f"API Error: {response_data['error']['message']}", status=500)

                generated_text = response_data['choices'][0]['message']['content']

            except requests.exceptions.RequestException as e:
                return HttpResponse(f"API Request Failed: {e}", status=500)
            except (KeyError, IndexError):
                return HttpResponse(f"Failed to parse API response. Raw: {api_response.text}", status=500)

            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            formatted_text = generated_text.replace('\n', '<br/>')
            story = [Paragraph(formatted_text, styles["Normal"])]
            doc.build(story)
            pdf_bytes = buffer.getvalue()
            buffer.close()

            return HttpResponse(pdf_bytes, content_type='application/pdf',
                                headers={"Content-Disposition": 'attachment; filename="generated_output.pdf"'})

    else:
        form = ResumeForm()
    return render(request, 'index.html', {'form': form})
