# Inrim Forms 

Forms is a project make form with formio builder and render with CRUD Api that implement italian [AGID Theme](https://github.com/italia/bootstrap-italia/) 

This project at build time download and add the repo [Form Templates Italia Theme](https://github.com/INRIM/forms-theme-italia)

Project is in WIP

## Features

- Design your form with Form.io builder for more info about Form.io see [Form.io homepage](https://www.form.io)
- View Form, the form is server side rendered with jinja template
- Add and Edit Data with yours forms

## Build and Test

- #### Config 
    - create a copy of .env.template:
    ```
    cp .env.template  .env-test
    ```
      
- #### Build and run      
    ```
    sh build_and_run_dev.sh
    ```

- #### app  
    ```
     http://localhost:9525/
    ```
    open [Forms Demo](http://localhost:9525/) in your browser
  

![Screen](gallery/design.png "Screen")

![Screen](gallery/enter_data.png "Screen")

## Depends on

* [FastApi](https://https://fastapi.tiangolo.com/.tiangolo.com/) - The Api framework
* [ODMantic](https://github.com/art049/odmantic) Asynchronous ODM(Object Document Mapper) for MongoDB
* [Jinja](https://github.com/pallets/jinja) - Jinja is a fast, expressive, extensible templating engine 
* [Form Templates Italia Theme](https://github.com/INRIM/forms-theme-italia)

Authors
------------

- Alessio Gerace

## License

This project is covered by a [license MIT](https://github.com/INRIM/inrim-forms/blob/master/LICENSE).