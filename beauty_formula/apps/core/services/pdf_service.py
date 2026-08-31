"""
Helper genérico de geração de PDF a partir de template Django, usando
WeasyPrint. Ponto único de renderização — reaproveitado tanto pelo
comprovante de quitação de comissão (payment) quanto pelos relatórios
em PDF (reports): geral, por funcionário, financeiro, de comissões.

Não sabe nada de domínio (comissão, agendamento, produto) — só recebe
um template + contexto e devolve bytes de PDF prontos pra virar
HttpResponse, FileField ou anexo de e-mail.
"""
from django.template.loader import render_to_string
from weasyprint import HTML


def render_pdf_from_template(template_name: str, context: dict) -> bytes:
    """Renderiza o template Django informado e converte o HTML resultante em PDF (bytes)."""
    html_string = render_to_string(template_name, context)
    return HTML(string=html_string).write_pdf()