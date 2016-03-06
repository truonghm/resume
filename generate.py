import copy
from glob import iglob
from hashlib import md5
from os import makedirs
from os.path import basename, exists, join, splitext
from re import sub
import shutil
from subprocess import call
from time import localtime, strftime

from git import Repo
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from yaml import load


with open("config.yaml") as configuration_file:
    config = load(configuration_file)
makedirs(config["BUILD_DIR"], exist_ok=True)
makedirs(join(config["OUTPUT_DIR"], config["LETTERS_DIR"]), exist_ok=True)

last_updated = localtime(Repo().head.commit.committed_date)
last_updated_string = strftime(config["DATE_FMT"], last_updated)


def main():
    with open(join(config["YAML_DIR"],
                   config["YAML_MAIN"] + ".yaml")) as resume_data:
        data = load(resume_data)
    with open(join(config["YAML_DIR"],
                   config["YAML_STYLE"] + ".yaml")) as style_data:
        data.update(**load(style_data))
    with open(join(config["YAML_DIR"],
                   config["YAML_BUSINESSES"] + ".yaml")) as business_data:
        businesses = load(business_data)

    if any("publications" in item for item in data["order"]):
        if not "publications" in data:
            with open(
                join(config["YAML_DIR"], config["YAML_PUBLICATIONS"] + ".yaml")
            ) as pub_data:
                pubs = load(pub_data)
            if pubs:
                data["publications"] = pubs
            else:
                for item in data["order"]:
                    if "publications" in item:
                        data["order"].remove(item)
                        break

    hashes = {f: md5_hash(f)
              for f in iglob("{}/*.tex".format(config["BUILD_DIR"]))}

    process_resume(HTML_CONTEXT, data)
    process_resume(LATEX_CONTEXT, data)
    process_resume(MARKDOWN_CONTEXT, data)

    if businesses:
        for business in businesses:
            data["business"] = businesses[business]
            data["business"]["body"] = LATEX_CONTEXT.render_template(
                config["LETTER_FILE_NAME"], data
            )
            process_resume(LATEX_CONTEXT, data, base=business)

    compile_latex(hashes)
    copy_to_output()


def process_resume(context, data, base=config["BASE_FILE_NAME"]):
    rendered_resume = context.render(data)
    context.write(rendered_resume, base=base)


def compile_latex(hashes):
    for input_file in iglob("{}/*.tex".format(config["BUILD_DIR"])):
        if (input_file in hashes and md5_hash(input_file) != hashes[input_file]
                or not exists(input_file.replace(".tex", ".pdf"))):
            call("xelatex -output-dir={} {}".format(config["BUILD_DIR"],
                                                    input_file).split())


def copy_to_output():
    for ext in ("pdf", "md", "html"):
        for file in iglob("{}/*.{}".format(config["BUILD_DIR"], ext)):
            if basename(file).startswith("0_"):
                shutil.copyfile(file,
                                join(config["OUTPUT_DIR"], basename(file)[2:]))
            else:
                shutil.copy(file, join(config["OUTPUT_DIR"],
                                       config["LETTERS_DIR"]))


def md5_hash(filename):
    with open(filename) as fin:
        return md5(fin.read().encode()).hexdigest()


class ContextRenderer(object):
    def __init__(self, context_name, filetype, jinja_options, replacements):
        self.filetype = filetype
        self.replacements = replacements

        context_templates_dir = join(config["TEMPLATES_DIR"], context_name)

        self.base_template = config["BASE_FILE_NAME"]
        self.context_name = context_name
        self.context_type_name = self.context_name + "type"

        self.jinja_options = jinja_options.copy()
        self.jinja_options["loader"] = FileSystemLoader(
            searchpath=context_templates_dir
        )
        self.jinja_options["undefined"] = StrictUndefined
        self.jinja_env = Environment(**self.jinja_options)

        self.known_types = [splitext(basename(s))[0]
                            for s in iglob(join(context_templates_dir,
                                                config["SECTIONS_DIR"],
                                                "*{}".format(self.filetype)))]

    def make_replacements(self, data):
        data = copy.copy(data)

        if isinstance(data, str):
            for o, r in self.replacements:
                data = sub(o, r, data)

        elif isinstance(data, dict):
            for k, v in data.items():
                data[k] = self.make_replacements(v)

        elif isinstance(data, list):
            for idx, item in enumerate(data):
                data[idx] = self.make_replacements(item)

        return data

    def render_template(self, template_name, data):
        full_name = template_name + self.filetype
        return self.jinja_env.get_template(full_name).render(**data)

    @staticmethod
    def _make_double_list(items):
        double_list = [{"first": items[i * 2], "second": items[i * 2 + 1]}
                       for i in range(len(items) // 2)]
        if len(items) % 2:
            double_list.append({"first": items[-1]})
        return double_list

    # noinspection PyTypeChecker
    def render(self, data):
        print("Rendering {} résumé".format(self.context_name))
        data = self.make_replacements(data)
        self._name = data["name"]["abbrev"]

        body = ""
        for (section_tag, show_title, section_title,
             section_type) in data["order"]:
            print(" +Processing section: {}".format(section_tag))
            section_data = {"name": section_title} if show_title else {}
            if section_tag == "NEWPAGE":
                section_content = None
            else:
                section_content = data[section_tag]
            section_data["items"] = section_content
            section_data["theme"] = data["theme"]

            if section_type and section_type.startswith(self.context_type_name):
                section_type = section_type.split("_", maxsplit=1)[1]
            if not section_type and section_tag in self.known_types:
                section_type = section_tag
            if section_type not in self.known_types:
                section_type = config["DEFAULT_SECTION"]

            section_data["type"] = section_type

            if section_type == "double_items":
                section_data["items"] = self._make_double_list(
                    section_data["items"])

            section_template_name = join(config["SECTIONS_DIR"], section_type)

            rendered_section = self.render_template(
                section_template_name, section_data)
            body += rendered_section.rstrip() + "\n\n\n"

        data["body"] = body
        data["updated"] = last_updated_string

        return self.render_template(self.base_template, data).rstrip() + "\n"

    def write(self, output_data, base=config["BASE_FILE_NAME"]):
        if base == config["BASE_FILE_NAME"]:
            prefix = "0_"
        else:
            prefix = ""
        output_file = join(config["BUILD_DIR"],
                           "{prefix}{name}_{base}{ext}".format(prefix=prefix,
                                                               name=self._name,
                                                               base=base,
                                                               ext=self.filetype
                                                               )
                           )
        with open(output_file, "w") as fout:
            fout.write(output_data)


LATEX_CONTEXT = ContextRenderer(
    "latex",
    ".tex",
    dict(
        block_start_string='~<',
        block_end_string='>~',
        variable_start_string='<<',
        variable_end_string='>>',
        comment_start_string='<#',
        comment_end_string='#>',
        trim_blocks=True,
        lstrip_blocks=True,
    ),
    []
)


MARKDOWN_CONTEXT = ContextRenderer(
    'markdown',
    '.md',
    dict(
        trim_blocks=True,
        lstrip_blocks=True
    ),
    [
        (r'\\ ', ' '),                      # spaces
        (r'\\textbf{([^}]*)}', r'**\1**'),  # bold text
        (r'\\textit{([^}]*)}', r'*\1*'),    # italic text
        (r'\\LaTeX', 'LaTeX'),              # \LaTeX to boring old LaTeX
        (r'\\TeX', 'TeX'),                  # \TeX to boring old TeX
        ('---', '-'),                       # em dash
        ('--', '-'),                        # en dash
        (r'``([^\']*)\'\'', r'"\1"'),       # quotes
    ]
)


HTML_CONTEXT = ContextRenderer(
    'html',
    '.html',
    dict(
        trim_blocks=True,
        lstrip_blocks=True
    ),
    [
        (r'\\ ', '&nbsp;'),                              # spaces
        (r'\\textbf{([^}]*)}', r'<strong>\1</strong>'),  # bold
        (r'\\textit{([^}]*)}', r'<em>\1</em>'),          # italic
        (r'\\LaTeX', 'LaTeX'),                           # \LaTeX
        (r'\\TeX', 'TeX'),                               # \TeX
        ('---', '&mdash;'),                              # em dash
        ('--', '&ndash;'),                               # en dash
        (r'``([^\']*)\'\'', r'"\1"'),                    # quotes
    ]
)


if __name__ == '__main__':
    main()
