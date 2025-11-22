# controleprocessos/arquiteturaprocessos/templatetags/form_tags.py
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def disable_field(field, css_classes="bg-gray-100 text-black"):
    """
    Desabilita o campo (readonly + disabled) e adiciona classes CSS opcionais.
    Usa como: {{ field|disable_field }} ou {{ field|disable_field:"classe-css" }}
    """
    attrs = {
        "readonly": "readonly",
        "disabled": "disabled",
        "class": css_classes
    }
    return mark_safe(field.as_widget(attrs=attrs))

@register.filter(name='add_class')
def add_class(field, css_class):
    """
    Adiciona classes CSS ao widget de um campo do formulário.
    Uso: {{ field|add_class:"minha-classe" }}
    """
    existing_classes = field.field.widget.attrs.get("class", "")
    new_class = f"{existing_classes} {css_class}".strip()

    return field.as_widget(attrs={**field.field.widget.attrs, "class": new_class})

@register.filter(name='add_attr')
def add_attr(field, attr):
    """
    Adiciona atributos HTML ao widget.
    Funciona mesmo quando o campo já foi renderizado (SafeString).
    """
    # Se for SafeString (HTML já renderizado)
    from django.utils.safestring import SafeString
    if isinstance(field, SafeString):
        # Injetar atributo diretamente no HTML
        key, value = attr.split(":", 1)
        insertion = f' {key}="{value}"'
        html = str(field)

        # insere antes do fechamento do primeiro > do widget
        index = html.find('>')
        if index != -1:
            html = html[:index] + insertion + html[index:]
        return mark_safe(html)

    # Caso normal: BoundField
    key, value = attr.split(":", 1)
    attrs = field.field.widget.attrs.copy()
    attrs[key] = value
    return field.as_widget(attrs=attrs)
