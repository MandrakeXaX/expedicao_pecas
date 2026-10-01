"""Filtros por dias corridos de espera, inclusivos nos limites."""
def filter_waiting(frame, mode='Todos', minimum=0, maximum=None):
    days=frame['dias_aguardando']
    if mode=='Todos':return frame
    if mode=='Exatamente':return frame[days==minimum]
    if mode=='Pelo menos':return frame[days>=minimum]
    if mode=='Entre':
        if maximum is None or maximum<minimum:raise ValueError('O máximo deve ser maior ou igual ao mínimo.')
        return frame[(days>=minimum)&(days<=maximum)]
    raise ValueError('Filtro de dias inválido.')
