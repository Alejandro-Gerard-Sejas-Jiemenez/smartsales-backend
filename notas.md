## notas del desarrollo
### link de la documentacion:

https://docs.google.com/document/d/1SBf6Vo6FvbQgA7vi2iW9b53WT75j9e6VQgtbJpVcEcY/edit?usp=sharing


### como activar el entorno virtual

1. ubicarse en la raiz
2. digitar

```bash
.\venv\Scripts\activate
```

### como crear apps
#### app= modulo independiente que agrupa modelos, rutas, logicas...

```bash
// si se quiere crear en la raiz
python manage.py startapp nombre_de_app 
// si se quiere crear en una ruta, la carpeta destino ya debe estar creada con el mismo nombre de la app
python manage.py startapp nombre_de_app ruta_desde_la_raiz/nombre_de_app
```

### flujo para completar una app
1. agregar app en config/settings.py
2. definir modelo models.py se crea clases 
3. serializer  traductor entre la tabla de la db y la api 
4. views.py    logica de endpoint
5. urls.py      
6. config/urls.py
7. probar endpoints

## Instalación de dependencias Django

Para instalar las dependencias del proyecto Django, ejecuta:

```powershell
pip install -r requirements.txt
```


### comandos de migracion:
##### si requiere app
`python manage.py makemigrations app`
`python manage.py makemigrations`
`python manage.py migrate`

### como correr el backend

```bash
    python manage.py runserver
```
