def institucion_actual(request):
    nombre = "TesisTrack"
    logo = None
    institucion = None

    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated:
        institucion = getattr(user, 'institucion', None)
        if institucion:
            nombre = institucion.nombre
            logo = institucion.logo

    return {
        'institucion_actual': institucion,
        'nombre_institucion': nombre,
        'logo_institucion': logo,
    }