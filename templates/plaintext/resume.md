{{ name.first }} {{ name.last }}
{{ "=" * (name.first|length + 1 + name.last|length) }}
PDF: {{ pdf }}
{#
source: {{ source }}
#}
Last updated: {{ updated }}

{{ extra_info }}

Contact information:
  email: {{ contact.email }}
  {% if contact.mobile is defined %}
  mobile: {{ contact.mobile }}
  {% endif %}
  {% if contact.website is defined %}
  website: {{ contact.website }}
  {% endif %}
  {% if contact.github is defined %}
  github: {{ contact.github }}
  {% endif %}
  {% if contact.linkedin is defined %}
  linkedin: {{ contact.linkedin }}
  {% endif %}


{{ body }}
