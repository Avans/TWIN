from constance import config

def constance(request):
    # return the value you want as a dictionnary. you may add multiple values in there.
    return {'CONSTANCE_CONFIG': config}