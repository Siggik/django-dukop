from django import template
from django.contrib import messages
from django.forms import BaseForm

register = template.Library()


@register.inclusion_tag("includes/forms/form.html", takes_context=True)
def dukop_form(context, form_obj):
    if not isinstance(form_obj, BaseForm):
        raise TypeError(
            "Error including form, it's not a form, it's a %s" % type(form_obj)
        )
    context.update({"form": form_obj})
    return context


@register.filter()
def dukop_render_field(field, extra_class=""):

    return field.as_widget(attrs={"class": "form-control " + extra_class})


@register.filter()
def message_css_class(message):
    """Takes a message object from django.contrib.message and returns
    a bootstrap danger/warning/info/success/default CSS class"""
    lvl = message.level
    if lvl >= messages.ERROR:
        return "danger"
    if lvl >= messages.WARNING:
        return "warning"
    if lvl >= messages.SUCCESS:
        return "success"
    if lvl >= messages.INFO:
        return "info"
    return "default"


@register.filter_function
def equals_string(value1, value2):
    return str(value1) == str(value2)
