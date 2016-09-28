{% extends "section.md" %}

{% block body %}
{% for pub in items %}
"{{ pub.title }}."
{{ pub.authors }}.
{{ pub.venuetype }} {{ pub.venue }}, {% if pub.month is defined %}{{ pub.month }} {% endif %}{{ pub.year }}.

{% endfor %}
{% endblock body %}
