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
    raise ValueError("Error in Loading OPENAI_API_KEY.env")

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
                    {"role": "system", "content": """“You are a Senior HR specializing in ATS-friendly resume optimization. Produce output in plain text only, suitable for ReportLab. No markdown tables, no code blocks, no images, no links.”

User:
“JD: <paste_job_description>
Resume: <extracted_resume_text>

Generate:

OPTIMISED RESUME

Name:

Contact:

Summary:

Skills: <comma-separated or simple bullets prefixed with '- '>

Experience:

Company | Role | Dates

Bullet 1

Bullet 2

Education:

Projects (optional):

EXPLANATION OF CHANGES

Keywords added: <comma-separated>

Formatting improvements:

...

ATS considerations:

...

Rules:

Use only plain text with '- ' bullets.

Keep Experience bullets achievement-oriented with metrics if present.

Incorporate JD keywords naturally.

Do not add any other sections or commentary.”

Bottom line
Inputs: PDF and JD text satisfied; DOC/DOCX not yet.

Outputs: Resume optimization mostly satisfied; explanation section not reliably enforced.

Skills: Partially demonstrated; strengthen prompt design, keyword extraction, and structure enforcement.

Implement the above adjustments to fully satisfy the task conditions end-to-end. If helpful, I can provide exact code changes for:

DOCX parsing branch,

Updated prompt payload,

Simple JD keyword extraction and inclusion check,

Response validation before PDF generation."""},
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
