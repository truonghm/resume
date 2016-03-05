import os
from time import localtime, strftime

import git
import jinja2
import yaml


date_format = "%Y--%m--%d"
last_updated = localtime(git.Repo().head.commit.committed_date)
last_updated_string = strftime(date_format, last_updated)

os.makedirs("build", exist_ok=True)
os.makedirs("output/with_letters", exist_ok=True)


latex = jinja2.Environment(
    block_start_string='~<',
    block_end_string='>~',
    variable_start_string='<<',
    variable_end_string='>>',
    comment_start_string='<#',
    comment_end_string='#>',
    trim_blocks=True,
    lstrip_blocks=True,
    loader=jinja2.FileSystemLoader(os.path.abspath('.')),
)


def main():
    main_template = latex.get_template("templates/latex/resume.tex")
    body_template = latex.get_template("templates/latex/letter_body.tex")

    with open("resume.yaml") as resume_data:
        data = yaml.load(resume_data)
    file_root = data["name"]["abbrev"]
    data["updated"] = last_updated_string

    with open("businesses.yaml") as businesses_data:
        businesses = yaml.load(businesses_data)

    for business in businesses:
        body = body_template.render(**data, **businesses[business])
        businesses[business]["body"] = body
        with open("build/{}_{}.tex".format(file_root, business), "w") as resume:
            resume.write(main_template.render(
                **data,
                business=businesses[business],
            ))

    with open("build/{}_resume.tex".format(file_root), "w") as resume:
        resume.write(main_template.render(
            **data,
        ))


if __name__ == '__main__':
    main()
