from custom_functions import *
from menu_utils import load_menu
import requests
import json



menu = load_menu('menu.xml')

lexicon_O = [v['nome'].lower() for v in menu.values()]

menulbl_to_id = {t:i for i,t in enumerate(lexicon_O)}
id_to_menulbl = {v:k for k,v in menulbl_to_id.items()}
id_to_prezzo = {i:v['prezzo'] for i,v in enumerate(menu.values())}

# tint_url = "http://localhost:8012/tint?"
# for index,t in enumerate(lexicon_O):
# 	response = requests.get(tint_url+'text='+t+'&format=json')
# 	annotations = json.loads(response.text)
# 	splitted = t.split()
# 	for i in annotations['sentences'][0]['tokens']:
# 		if 'features' in i:
# 			if 'Number'in i['features']:
# 				if i['features']['Number'][0] == 'Plur':
# 					splitted[i['index']-1] = i['lemma']
# 					lexicon_O[index] = ' '.join(splitted)

# menulbllemma_to_id = {t:i for i,t in enumerate(lexicon_O)}


lexicon_TO = ['menu','forchetta','coltello','bicchiere']
lexicon_I = ['antipasto','primo','secondo','dolce']
lexicon_P = ['conto']

frames = [{'name':'ORDINAZIONE','lu_v':['potere','mangiare','ordinare','volere','chiedere','portare','prendere'],'lu_s':lexicon_O,'ce':['entity']},
	   	  {'name':'TR_OGGETTO','lu_v':['portare'],'lu_s':lexicon_TO,'ce':['theme']},
	   	  {'name':'INFORMAZIONE','lu_v':['elencare','essere','avere','dire'],'lu_s':lexicon_I,'ce':['content']},
	   	  {'name':'PAGAMENTO','lu_v':['portare','pagare','saldare'],'lu_s':lexicon_P,'ce':['good']}]


short_term = []
long_term = []

world_state = ['0','0','0','0','0']

#===============================================================================================================
#=========================================== STATES ============================================================

ATTESA = {'eff':'***00',
		  'turn':'Digitare T per chiamare al tavolo\n\t\t E per far entrare un nuovo cliente',
		  'input':'',
		  'successors_f':attesa_suc,
		  'successors':[{'name':'BENVENUTO','pre':'','in':'E'},
		  				{'name':'TAVOLA','in':'T','pre':'1****'},
		  				{'name':'SALA_VUOTA','in':'T','pre':'0****'},
		  				{'name':'ATTESA_UNK','in':'','pre':''}],
		  'name':'ATTESA',
		  'priority':1
		 }


ATTESA_UNK = {'turn':'Digitare T per chiamare al tavolo\n\t\t E per far entrare un nuovo cliente',
		      'successors':[{'name':'ATTESA'}],
		  	  'name':'ATTESA_UNK',
		  	  'priority':1}


SALA_VUOTA = {'turn':':P',
			  'successors':[{'name':'ATTESA'}],
			  'name':'SALA_VUOTA',
			  'priority':1}


BENVENUTO = {'eff':'*1*11',
			 'turn':'Benvenuto, io sono Ennio. Quanti siete?',
			 'input':'',
			 'successors_f':benvenuto_succ,
		  	 'successors':[{'name':'PRENOTAZIONE_1','in':1,'pre':'0****'},
		  	 			   {'name':'PRENOTAZIONE_0','in':1,'pre':'1****'},
		  	 			   {'name':'PRENOTAZIONE_2','in':2,'pre':''},
		  	 			   {'name':'BENVENUTO_UNK','in':'','pre':''}],
		  	 'name':'BENVENUTO',
		  	 'priority':1
		  	}


BENVENUTO_UNK = {'turn':'Mi dispiace non ho capito. Potresti ripetere?',
				 'input':'',
				 'successors_f':benvenuto_succ,
			  	 'successors':[{'name':'PRENOTAZIONE_1','in':1,'pre':'0****'},
			  	 			   {'name':'PRENOTAZIONE_0','in':1,'pre':'1****'},
			  	 			   {'name':'PRENOTAZIONE_2','in':2,'pre':''},
			  	 			   {'name':'BENVENUTO_UNK','in':'','pre':''}],
		  	 	 'name':'BENVENUTO_UNK',
		  	 	 'priority':1
		  		}


PRENOTAZIONE_1 = {'eff':'10*0*',
				  'turn':prenotazione1_tur,
				  'exec':prenotazione1_exe,
				  'successors':[{'name':'ATTESA'}],
				  'name':'PRENOTAZIONE_1',
				  'priority':1
				  }

PRENOTAZIONE_0 = {'eff':'*0*0*',
				  'turn':'Mi dispiace ma siamo al completo, prova a passare più tardi.',
				  'successors':[{'name':'ATTESA'}],
				  'name':'PRENOTAZIONE_0',
				  'priority':1}

PRENOTAZIONE_2 = {'eff':'*0*0*',
				  'turn':'Mi dispiace ma non posso gestire tavolate così grandi.',
				  'successors':[{'name':'ATTESA'}],
				  'name':'PRENOTAZIONE_2',
				  'priority':1}

TAVOLA = {'eff':'***21',
			'turn':'Dimmi pure',
			'input':'',
			'successors_f':tavola_suc,
		  	 'successors':[{'name':'ORDINAZIONE','in':frames[0],'pre':''},
		  	 			   {'name':'ORDINAZIONE_CONFERMA','in':frames[0],'pre':''},
		  	 			   {'name':'TR_OGGETTO','in':frames[1],'pre':''},
		  	 			   {'name':'INFORMAZIONE','in':frames[2],'pre':''},
		  	 			   {'name':'PAGAMENTO_1','in':frames[3],'pre':'**1**'},
		  	 			   {'name':'PAGAMENTO_0','in':frames[3],'pre':'**0**'},
		  	 			   {'name':'NOIN','in':'','pre':''},
		  	 			   {'name':'TAVOLA_UNK','in':'','pre':''}],
			'name':'TAVOLA',
			'priority':1}

NOIN = {'turn':noin_tur,
		'successors':[{'name':'ATTESA'}],
		'name':'NOIN',
		'priority':1}

PAGAMENTO_0 = {'eff':'00000',
			   'turn':'Non ha ordinato nulla, il suo conto è pari a 0. Grazie e arrivederci.',
			   'successors':[{'name':'ATTESA'}],
			   'name':'PAGAMENTO_0',
			   'priority':1}


PAGAMENTO_1 = {'eff':'00000',
			   'turn':pagamento1_tur,
			   'successors':[{'name':'ATTESA'}],
			   'name':'PAGAMENTO_1',
			   'priority':1}


TAVOLA_UNK = {'turn':'Mi dispiace non ho capito. Potresti ripetere?',
			  'input':'',
			  'successors_f':tavola_suc,
		  	  'successors':[{'name':'ORDINAZIONE','in':frames[0],'pre':''},
		  	  				{'name':'ORDINAZIONE_CONFERMA','in':frames[0],'pre':''},
		  	 			    {'name':'TR_OGGETTO','in':frames[1],'pre':''},
		  	 			    {'name':'INFORMAZIONE','in':frames[2],'pre':''},
		  	 			    {'name':'PAGAMENTO_1','in':frames[3],'pre':'**1**'},
		  	 			    {'name':'PAGAMENTO_0','in':frames[3],'pre':'**0**'},
		  	 			    {'name':'NOIN','in':'','pre':''},
		  	 			    {'name':'TAVOLA_UNK','in':'','pre':''}],
			  'name':'TAVOLA_UNK',
			  'priority':1
		   	 }


ORDINAZIONE = {'eff':'**1**',
			   'memory':ordinazione_mem,
			   'successors':[{'name':'ORDINAZIONE_ITER'}],
			   'name':'ORDINAZIONE',
			   'priority':3
				}


ORDINAZIONE_ITER = {'turn':ord_iter_tur, #random choice fra alcune frasi del tipo (e poi?)
					'input':'',
					'successors_f':ord_iter_succ, #simile a inputframe_succ ma con la root fissa a "portami un" perchè è prevista solo l'ordinazione!!!
					'successors':[{'name':'ORDINAZIONE','in':frames[0],'pre':''},
		  	  					  {'name':'ORDINAZIONE_CONFERMA','in':frames[0],'pre':''},
		  	  					  {'name':'RIEPILOGO','in':'(no.*|.*basta.*|.*no basta.*)','pre':''},
		  	  					  {'name':'ORDINAZIONE_ITER_UNK','in':'','pre':''}],
		  	  		'name':'ORDINAZIONE_ITER',
		  	  		'priority':1
					}


ORDINAZIONE_ITER_UNK = {'turn':'Mi dispiace non ho capito. Potresti ripetere?',
						'input':'',
						'successors_f':ord_iter_succ, #simile a inputframe_succ ma con la root fissa a "portami un" perchè è prevista solo l'ordinazione!!!
						'successors':[{'name':'ORDINAZIONE','in':frames[0],'pre':''},
			  	  					  {'name':'ORDINAZIONE_CONFERMA','in':frames[0],'pre':''},
			  	  					  {'name':'ORDINAZIONE_ITER_UNK','in':'','pre':''}],
			  	  		'name':'ORDINAZIONE_ITER',
			  	  		'priority':1
						}

ORDINAZIONE_CONFERMA = {'turn':ord_conf_tur, #deve guardare in memoria (per acchiappare i piatti questo o quello)
						'input':'',
						'successors_f':ord_conf_succ, #deve guardare in memoria (per acchiappare cosa ha detto il cliente e restringere la grammatica)
						'successors':[{'name':'ORDINAZIONE','in':'mem','pre':''},
		  	  						  {'name':'ORDINAZIONE_CONFERMA_UNK','in':'','pre':''}],
		  	  			'name':'ORDINAZIONE_CONFERMA',
		  	  			'priority':1
		  	  		    }

ORDINAZIONE_CONFERMA_UNK = {'turn':'Mi dispiace non ho capito. Potresti ripetere?', #deve guardare in memoria
							'input':'',
							'successors_f':ord_conf_succ, #deve guardare mem per acchiappare cosa ha detto il cliente
							'successors':[{'name':'ORDINAZIONE','in':'mem','pre':''},
		  	  						  	  {'name':'ORDINAZIONE_CONFERMA_UNK','in':'','pre':''}],
		  	  				'name':'ORDINAZIONE_CONFERMA_UNK',
		  	  				'priority':1
		  	  		    	}



RIEPILOGO = {'turn':riepilogo_tur,
			 'successors':[{'name':'HELP'}],
			 'name':'RIEPILOGO',
			 'priority':2
			}

HELP = {'turn':'Posso fare altro?',
		'input':'',
		'successors_f':help_succ,
		'successors':[{'name':'ATTESA','in':'no.*','pre':''},
		  	  			{'name':'TAVOLA','in':'si.*','pre':''},
		  	  			{'name':'HELP_UNK','in':'','pre':''}],
		'name':'HELP',
		'priority':1
		}

HELP_UNK = {'turn':'Mi dispiace non ho capito. Potresti ripetere?',
			'input':'',
			'successors_f':help_succ,
			'successors':[{'name':'ATTESA','in':'si.*','pre':''},
			  	  			{'name':'TAVOLA','in':'no.*','pre':''},
			  	  			{'name':'HELP_UNK','in':'','pre':''}],
			'name':'HELP_UNK',
			'priority':1
			}


TR_OGGETTO = {'turn':tr_oggetto_tur,
		  	  'successors':[{'name':'ATTESA'}],
		  	  'name':'TR_OGGETTO',
		  	  'priority':1}
				   

INFORMAZIONE = {'turn':informazione_tur,
				'successors':[{'name':'ATTESA'}],
				'name':'INFORMAZIONE',
				'priority':1}



FSA = {'ATTESA':ATTESA,
	   'ATTESA_UNK':ATTESA_UNK,
	   'SALA_VUOTA':SALA_VUOTA,
	   'BENVENUTO':BENVENUTO,
	   'BENVENUTO_UNK':BENVENUTO_UNK,
	   'PRENOTAZIONE_0':PRENOTAZIONE_0,
	   'PRENOTAZIONE_1':PRENOTAZIONE_1,
	   'PRENOTAZIONE_2':PRENOTAZIONE_2,
	   'TAVOLA':TAVOLA,
	   'TAVOLA_UNK':TAVOLA_UNK,
	   'NOIN':NOIN,
	   'PAGAMENTO_0':PAGAMENTO_0,
	   'PAGAMENTO_1':PAGAMENTO_1,
	   'ORDINAZIONE':ORDINAZIONE,
	   'ORDINAZIONE_ITER':ORDINAZIONE_ITER,
	   'ORDINAZIONE_ITER_UNK':ORDINAZIONE_ITER_UNK,
	   'ORDINAZIONE_CONFERMA':ORDINAZIONE_CONFERMA,
	   'ORDINAZIONE_CONFERMA_UNK':ORDINAZIONE_CONFERMA_UNK,
	   'HELP':HELP,
	   'HELP_UNK':HELP_UNK,
	   'RIEPILOGO':RIEPILOGO,
	   'TR_OGGETTO':TR_OGGETTO,
	   'INFORMAZIONE':INFORMAZIONE}
