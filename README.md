About
-----
This repo contains the source I use to automatically generate [my résumé]
(http://github.com/masasin/resume) as a webpage and PDF from YAML input.

Samples are in the [samples](http://github.com/masasin/resume/samples) directory.
Note that they were automatically generated, as opposed to optimized separately.

It was forked from [emichael/resume](https://github.com/emichael/resume),
which was in turn forked from [bamos/cv](https://github.com/bamos/cv).
I have added the ability to automatically generate PDFs with cover letters,
as well as have separate input files.

See the original repo for details about the choices of YAML, LaTeX, and Markdown.


How to run
----------
You will need Python 3, git, and LaTeX installed on your computer.

The dependencies are included in `requirements.txt` and can be installed using
`pip` with `pip install -r requirements.txt`. I recommend doing this inside a
`virtualenv`.

To run, call `generate.py`, which will look for YAML files in the input directory.


What to Modify
--------------
You can change folders or file naming in `config.yaml`.
The names used in the README are the default values.
You can change any of the YAML files in the `inputs` directory.
The image file in `img`, should you be using one, also needs to change.
Finally, take a look at the `templates` directory to see if you want to edit anything.

The main résumé is in `resume.yaml`.
You can change the order of items in the `order` section.
`publications.yaml` should contain all the publications you want to show.
Finally, `businesses.yaml` should contain details about prospective employers.
Each YAML file contains documentation showing which fields can be used and which are optional.

A cover letter will be automatically generated for each business from `templates/latex/letter_body.tex`.
Don't forget to edit that file.
All the resulting PDFs will be named appropriately and stored in the `outputs/cover_letters` directory.

### Warnings
1. Strings in `resume.yaml` should be LaTeX (though, the actual LaTeX formatting
   should be in the left in the templates as much as possible).
2. If you do include any new LaTeX commands, make sure that one of the
   `REPLACEMENTS` in `generate.py` converts them properly.
3. The LaTeX templates use modified Jinja delimiters to avoid overlaps with
   normal LaTeX. See `generate.py` for details.
4. LaTeX files are only regenerated when the source changes or when the PDF
   does not exist.
5. By default, the update date changes based on the time of the latest git commit on the current branch.
   You can change it in `resume.yaml`


License
-------
All of bamos's and emichael's original work is distributed under the MIT license
found in `LICENSE-bamos.mit` and `LICENSE-emichael.mit` respectively.

My modifications are distributed under the MIT license found in
`LICENSE-masasin.mit`.
