from custom_functions import *
from menu_utils import load_menu
import requests
import json



menu = load_menu('menu.xml')

lexicon_O = [v['nome'].lower() for v in menu.values()]


portata_to_menulbl={}
for k,v in menu.items():
	if v['tipo'] not in portata_to_menulbl:
		portata_to_menulbl[v['tipo']] = [k.lower()]
	else:
		portata_to_menulbl[v['tipo']].append(k.lower())


lexicon_TO = ['menu','forchetta','coltello','bicchiere']
lexicon_I = ['antipasto','primo','secondo','dolcio']
lexicon_P = ['conto']

frames = [{'name':'ORDINAZIONE','lu_v':['potere','mangiare','ordinare','volere','chiedere','portare','prendere'],'lu_s':lexicon_O,'ce':['entity']},
	   	  {'name':'TR_OGGETTO','lu_v':['portare'],'lu_s':lexicon_TO,'ce':['theme']},
	   	  {'name':'INFORMAZIONE','lu_v':['elencare','essere','avere','dire'],'lu_s':lexicon_I,'ce':['content']},
	   	  {'name':'PAGAMENTO','lu_v':['porgere','portare','pagare','saldare'],'lu_s':lexicon_P,'ce':['good']}]


short_term = []
long_term = []

world_state = ['0','0','0','0','0']

#===============================================================================================================
#=========================================== STATES ============================================================

ATTESA = {'eff':'***00',
		  'turn':'Digitare T per chiamare al tavolo\n\t E per far entrare un nuovo cliente',
		  'input':'',
		  'successors_f':attesa_suc,
		  'successors':[{'name':'BENVENUTO','pre':'','in':'E'},
		  				{'name':'TAVOLA','in':'T','pre':'1****'},
		  				{'name':'SALA_VUOTA','in':'T','pre':'0****'},
		  				{'name':'ATTESA','in':'','pre':''}],
		  'name':'ATTESA',
		  'priority':1
		 }


ATTESA_UNK = {'turn':'Digitare T per chiamare al tavolo\n\t E per far entrare un nuovo cliente',
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
			'turn':tavola_tur,
			'input':'',
			'successors_f':tavola_suc,
		  	 'successors':[{'name':'ORDINAZIONE','in':frames[0],'pre':''},
		  	 			   {'name':'ORDINAZIONE_CONFERMA','in':frames[0],'pre':''},
		  	 			   {'name':'TR_OGGETTO','in':frames[1],'pre':''},
		  	 			   {'name':'INFORMAZIONE','in':frames[2],'pre':''},
		  	 			   {'name':'PAGAMENTO','in':frames[3],'pre':''},
		  	 			   {'name':'QTY','in':'','pre':''},
		  	 			   {'name':'NOIN','in':'','pre':''},
		  	 			   {'name':'RIEPILOGO','in':'','pre':''},
		  	 			   {'name':'TAVOLA_UNK','in':'','pre':''}],
			'name':'TAVOLA',
			'priority':1}



TAVOLA_UNK = {'turn':'Mi dispiace non ho capito. Potresti ripetere?\nProva con\n"vorrei ordinare una crostata" oppure\n"potresti portarmi una forchetta" oppure\n"potresti elencare i primi piatti"',
			  'input':'',
			  'successors_f':tavola_suc,
		  	  'successors':[{'name':'ORDINAZIONE','in':frames[0],'pre':''},
		  	  				{'name':'ORDINAZIONE_CONFERMA','in':frames[0],'pre':''},
		  	 			    {'name':'TR_OGGETTO','in':frames[1],'pre':''},
		  	 			    {'name':'INFORMAZIONE','in':frames[2],'pre':''},
		  	 			    {'name':'PAGAMENTO','in':frames[3],'pre':''},
		  	 			    {'name':'QTY','in':'','pre':''},
		  	 			    {'name':'NOIN','in':'','pre':''},
		  	 			    {'name':'RIEPILOGO','in':'','pre':''},
		  	 			    {'name':'TAVOLA_UNK','in':'','pre':''}],
			  'name':'TAVOLA_UNK',
			  'priority':1}



NOIN = {'turn':noin_tur,
		'successors':[{'name':'TAVOLA'}],
		'name':'NOIN',
		'priority':1}

QTY = {'turn':'Mi dispiace ma ho solo 2 mani',
		'successors':[{'name':'TAVOLA'}],
		'name':'QTY',
		'priority':1}

PAGAMENTO = {'eff':'00000',
			 'turn':pagamento_tur,
			 'exec':pagamento_exe,
			 'successors':[{'name':'ATTESA'}],
			 'name':'PAGAMENTO',
			 'priority':1}

ORDINAZIONE = {'eff':'**1**',
			   'turn':'Ok, segnato',
			   'memory':ordinazione_mem,
			   'successors':[{'name':'TAVOLA'}],
			   'name':'ORDINAZIONE',
			   'priority':1}

TR_OGGETTO = {'turn':tr_oggetto_tur,
		  	  'successors':[{'name':'TAVOLA'}],
		  	  'name':'TR_OGGETTO',
		  	  'priority':1}
				   

INFORMAZIONE = {'turn':informazione_tur,
				'successors':[{'name':'TAVOLA'}],
				'name':'INFORMAZIONE',
				'priority':1}

RIEPILOGO = {'turn':riepilogo_tur,
			 'exec':riepilogo_exe,
			 'memory':riepilogo_mem,
			 'successors':[{'name':'ATTESA'}],
			 'name':'RIEPILOGO',
			 'priority':1
			}

ORDINAZIONE_CONFERMA = {'turn':ord_conf_tur, #deve guardare in memoria (per acchiappare i piatti questo o quello)
						'input':'',
						'memory':ord_conf_mem,
						'successors_f':ord_conf_succ, #deve guardare in memoria (per acchiappare cosa ha detto il cliente e restringere la grammatica)
						'successors':[{'name':'ORDINAZIONE','in':'mem','pre':''},
									  {'name':'ALT','in':'','pre':''},
		  	  						  {'name':'ORDINAZIONE_CONFERMA_UNK','in':'','pre':''}],
		  	  			'name':'ORDINAZIONE_CONFERMA',
		  	  			'priority':1
		  	  		    }

ORDINAZIONE_CONFERMA_UNK = {'turn':'Mi dispiace non ho capito. Potresti ripetere?', #deve guardare in memoria
							'input':'',
							'successors_f':ord_conf_succ, #deve guardare mem per acchiappare cosa ha detto il cliente
							'successors':[{'name':'ORDINAZIONE','in':'mem','pre':''},
										  {'name':'ALT','in':'','pre':''},
		  	  						  	  {'name':'ORDINAZIONE_CONFERMA_UNK','in':'','pre':''}],
		  	  				'name':'ORDINAZIONE_CONFERMA_UNK',
		  	  				'priority':1
		  	  		    	}

ALT = {'turn':'Ok, come preferisci',
		'successors':[{'name':'TAVOLA'}],
		'name':'ALT',
		'priority':1}


# HELP = {'turn':'Posso fare altro?',
# 		'input':'',
# 		'successors_f':help_succ,
# 		'successors':[{'name':'ATTESA','in':{'regex':'(no.*|(no|) puoi andare.*)'},'pre':''},
# 		  	  			{'name':'TAVOLA','in':{'regex':'si.*'},'pre':''},
# 		  	  			{'name':'HELP_UNK','in':'','pre':''}],
# 		'name':'HELP',
# 		'priority':1
# 		}

# HELP_UNK = {'turn':'Mi dispiace non ho capito. Potresti ripetere?',
# 			'input':'',
# 			'successors_f':help_succ,
# 			'successors':[{'name':'ATTESA','in':{'regex':'no.*'},'pre':''},
# 			  	  			{'name':'TAVOLA','in':{'regex':'si.*'},'pre':''},
# 			  	  			{'name':'HELP_UNK','in':'','pre':''}],
# 			'name':'HELP_UNK',
# 			'priority':1
# 			}






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
	   'PAGAMENTO':PAGAMENTO,
	   'ORDINAZIONE':ORDINAZIONE,
	   'ORDINAZIONE_CONFERMA':ORDINAZIONE_CONFERMA,
	   'ORDINAZIONE_CONFERMA_UNK':ORDINAZIONE_CONFERMA_UNK,
	   #'HELP':HELP,
	   #'HELP_UNK':HELP_UNK,
	   'RIEPILOGO':RIEPILOGO,
	   'TR_OGGETTO':TR_OGGETTO,
	   'INFORMAZIONE':INFORMAZIONE,
	   'ALT':ALT,
	   'QTY':QTY}

for k,v in FSA.items():
	for k1 in v.keys():
		assert k1 in ['successors','successors_f','turn','exec','input','name','priority','memory','eff']