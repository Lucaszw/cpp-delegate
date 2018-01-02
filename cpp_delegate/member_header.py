import io

import jinja2
import pydash as py_

__all__ = ['get_functions', 'render']


member_structs_template = jinja2.Template(r'''
{% for name_i, member_i in py_.sort(members) %}
typedef struct __attribute__((packed)) {
{%- for arg_ij in member_i.arguments %}
{{ '  ' + arg_ij.type + ' ' + arg_ij.name + ';' }}
{%- endfor %}
} {{ name_i }}__Request;

typedef struct __attribute__((packed)) {
{%- if member_i.result_type %}
{{ '  ' + member_i.result_type + ' result;' }}
{%- endif %}
} {{ name_i }}__Response;
{% endfor %}

{%- for name_i, member_i in py_.sort(members) %}
const uint32_t CMD__{{ name_i }} = {{ loop.index0 }};
{%- endfor %}
'''.strip())

member_switch_template = jinja2.Template(r'''
class Exec {
{% for name_i, member_i in py_.sort(members) %}
UInt8Array exec__CMD__{{ name_i }}(UInt8Array request_arr) {
    UInt8Array result = request_arr;
    // {{ member_i.result_type }} {{ name_i }}({% for a in member_i.arguments %}{{ ', ' if loop.index0 > 0 else ''}}{{ a.type }} {{ a.name }}{% endfor %});
    // {{ member_i.location }}
    {%- if member_i.arguments %}
    {{ name_i }}__Request &request = *(reinterpret_cast
                                        <{{ name_i }}__Request *>
                                        (&request_arr.data[0]));
    {%- endif %}
    {% if member_i.result_type %}
    {{ name_i }}__Response response;

    response.result = {% endif -%}
    {{ name_i }}({% for a in member_i.arguments %}{{ ', ' if loop.index0 > 0 else ''}}/* {{ a.type }} */ request.{{ a.name }}{% endfor %});

    {%- if member_i.result_type %}
    /* Copy result to output buffer. */
    /* Cast start of buffer as reference of result type and assign result. */
    {{ name_i }}__Response &output = *(reinterpret_cast
                                        <{{ name_i }}__Response *>
                                        (&request_arr.data[0]));
    output = response;
    result.data = request_arr.data;
    result.length = sizeof(output);
    {% else %}
    result = UInt8Array_init_default();
    {% endif %}
    return result;
}
{%- endfor %}
public:
UInt8Array operator () (uint32_t value, UInt8Array request_arr) {
    switch (value) {
{% for name_i, member_i in py_.sort(members) %}
        case CMD__{{ name_i }}:
            return exec__CMD__{{ name_i }}(request_arr);
            break;
{% endfor %}
        default:
        {
            UInt8Array result;
            result.data = request_arr.data;
            result.length = 0;
            return result;
        }
    }
    return UInt8Array_init_default();
}
};
'''.strip())


def get_functions(members):
    return [(v['name'], v)
            for v in py_.group_by(members.values(),
                                  lambda v: v['kind'])['FUNCTION_DECL']
            if not v['name'].startswith('operator ')
            and v['name'] not in ('analogWriteDAC1', '_restart_Teensyduino_',
                                  'init_pins', 'serialEvent4', 'serialEvent5',
                                  'serialEvent6')
            and not v['name'].startswith('serial4')
            and not v['name'].startswith('serial5')
            and not v['name'].startswith('serial6')
            and not any([a['kind'] == 'POINTER' for a in v['arguments']])
            and all([a['name'] for a in v['arguments']])]


def render(functions):
    header = io.BytesIO()

    print >> header, '''
#ifndef ___MEMBER_HEADER__H___
#define ___MEMBER_HEADER__H___'''
    print >> header, str(member_structs_template.render(members=functions,
                                                        py_=py_))
    print >> header, '\n'
    print >> header, str(member_switch_template.render(members=functions,
                                                       py_=py_))
    print >> header, '''
#endif  // #ifndef ___MEMBER_HEADER__H___'''
    return header.getvalue()
