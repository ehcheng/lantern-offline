#!/usr/bin/env python3
"""Build the four triage pages from ONE source, data/triage_src.html (FIXES #206, E6: English first).

  library/triage_v1.html     drive, English   (source minus every <span lang="es">, hand hrefs kept: no-script page)
  library/triage.html        server, English  (Lantern shell, refs resolved)
  library/triage_es_v1.html  drive, Spanish   (same cards, order and ids; #<card>-es aliases)
  library/triage_es.html     server, Spanish

English pages carry no Spanish except one small "Español" switch; an old triage.html#<card>-es link is forwarded to the Spanish page.
Usage: build_triage.py [OUTDIR]   (default library/; give a $TMPDIR folder for a dry run). Rerunnable."""
import html as H
import os
import re
import subprocess
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from refs import resolve   # <a data-ref="KEY"> -> real links (refs.json)
from gen_shelves import tabbar_html, brand_html, favicon_html   # one tab bar for every page; stamp_chrome re-stamps between the markers

LIB = os.path.abspath(os.path.join(HERE, "..", "library"))
SRC = os.path.abspath(os.path.join(HERE, "..", "data", "triage_src.html"))
D2_EN = ("This library's own pages, summaries and search never state drug doses. The medical books on the shelf do: "
         "use the printed drug guide (Davis's, Lippincott pocket) for any dose.")
D2_ES = ("Las páginas, los resúmenes y el buscador de esta biblioteca nunca indican dosis de medicamentos. Los libros de "
         "medicina del estante sí las traen: para cualquier dosis use la guía impresa de medicamentos (Davis's, Lippincott de bolsillo).")
ES_SPAN = re.compile(r'\s*<span id="([a-z]+-es|es)" lang="es">(.*?)</span>', re.S)
LABEL = re.compile(r'^\s*(?:<strong>)?en español:(?:</strong>)?\s*', re.I)
# an old triage.html#<card>-es (or #es) link lands on the English server page: forward it to the Spanish page.
# Not on triage_v1.html: the drive pages stay script-free (t8_plain static); its old #es lands on the switch (id="es").
FWD = ("<script>if(/^#(es|[a-z]+-es)$/.test(location.hash))location.replace('{es}'+location.hash)</script>")
SWITCH = '<p style="text-align:right;margin:0 0 4px;font-size:15px"><a {idattr}href="{href}" lang="{l}">{t}</a></p>'
# FIXES #219: an English NOW clause must keep its Spanish twin (the newborn line was lost from birth-es in the #206 split).
# ponytail: a safety-term list, not a translation check; add a pair when a card gains a new kind of clause.
TWINS = [(r"newborn|baby just born", r"reci[eé]n nacid"), (r"dengue", r"dengue"), (r"tourniquet", r"torniquete"),
         (r"\bCPR\b", r"\bRCP\b"), (r"poison control", r"control de envenenamientos"), (r"meningitis", r"meningitis"),
         (r"vomit", r"v[oó]mit"), (r"blister", r"ampolla"), (r"sugar", r"az[uú]car"), (r"insulin", r"insulina"),
         (r"\b24 hours", r"24 horas"), (r"\b3 hours", r"3 horas"), (r"\bmin(ute)?s?\b", r"minuto"), (r"\bfeet\b", r"\bpies\b"),
         (r"inches", r"pulgadas|\bcm\b"), (r"\bice\b", r"hielo"), (r"hospital", r"hospital"), (r"epinephrine", r"epinefrina"),
         (r"ending their life|suicid", r"quitarse la vida|suicid"), (r"placenta", r"placenta"), (r"rabies", r"rabia"),
         (r"mushroom", r"hongo"), (r"\bsalt\b", r"\bsal\b"), (r"\bboil", r"hierv"), (r"toilet tank", r"tanque del inodoro"),
         (r"do not wrap", r"no envuelva"), (r"stiff neck", r"cuello tieso"), (r"back or neck", r"cuello"),
         (r"wake them|waking", r"despi[eé]rt"), (r"paracetamol|ibuprofen|aspirin", r"paracetamol|ibuprofeno|aspirina"),
         # FIXES #232 (b3 W16-W20, N07): the clauses round 7 found without a twin
         (r"everyone out", r"salgan todos"), (r"chest wound", r"herida[^.]*pecho"), (r"frostbite", r"congelaci"),
         (r"= heat exhaustion", r"= agotamiento por calor"), (r"swelling of the face", r"hinchaz[oó]n de la cara"),
         (r"leave open", r"no cierre")]
# FIXES #242 (b3 B3-36): DEEPER situation clauses reach the Spanish reader too (the Spanish cards have no DEEPER line, so the
# twin sits in the card's Spanish line). Checked against the English DEEPER text only: its book titles ("Hospital Care") are noise.
DEEPER_TWINS = [(r"after splint", r"despu[eé]s de la tablilla"), (r"red streaks", r"l[ií]neas rojas"), (r"sunken eyes", r"ojos hundidos"),
                (r"blood in stool", r"con sangre"), (r"stiff neck", r"cuello tieso")]
# FIXES #232: a situation clause is "<situation>: <action>" or "<situation> = <action>" at a sentence start. A card's Spanish line
# must have at least as many as its English NOW, so a dropped clause fails the build even with no TWINS term in it.
# ponytail: punctuation heuristic; CLAUSE_SKIP holds the link labels ("WikiMed:", "Medics:") that are not situations.
CLAUSE = re.compile(r'(?:^|(?<=[.!;:·»”"])\s+)([^\s.:;=«»"·(][^.:;=«»"·]{2,160}?)\s*(?::|\s=\s)')
CLAUSE_SKIP = re.compile(r"^(NOW|En español|WikiMed|Medics|From a drive|Signs and prevention)$|\s—\s", re.I)


# FIXES #249 (round 9 class 5, b3 B3-29: the burns line cited PDF p.39 for the step on p.38): every cite in a card's NOW, DEEPER
# and Spanish line must hold the key words of the clause it backs, on the page it names (a PDF #page=N: that page; a mirror
# #anchor: from the anchor on; no fragment: the whole file). Keyed (card, href); a tuple = every pattern must hit; a list = one
# pattern per cite of that href on the card, and the count must match (so a cite moved to another page of the same PDF fails even
# when that page is cited elsewhere on the card). A local cite with no key, a key with no cite, a missing file or
# anchor, or a page without the words fails the build (b3_srccheck's rule).
# Not checked: live-server links (http), search.html fallbacks, plants.html routes (their README.txt fallback is), folders.
W, WS, WP, MSF, OB = ("mirrors/hesperian/en.hesperian.org/hhg/", "mirrors/hesperian/es.hesperian.org/hhg/",
                      "docs/medical/hesperian_where_there_is_no_doctor/en_nwtnd_2014_03g.pdf",
                      "docs/medical/msf/msf_clinical_guidelines.pdf", "docs/medical/msf/msf_obstetrics_newborn.pdf")
N, NS = W + "New_Where_There_Is_No_Doctor:", WS + "New_Where_There_Is_No_Doctor:"
HYPO, DENT = "docs/medical/tccc/Hypothermia_Prevention_Treatment.pdf", "docs/medical/hesperian_where_there_is_no_dentist.pdf"
IMCI, POCKET, MHGAP = ("docs/medical/who_imci_chart_booklet.pdf", "docs/medical/who_pocket_book_hospital_care_children.pdf",
                       "docs/medical/who_mhgap_intervention_guide_v2.pdf")
EPA2 = "docs/water/epa_emergency_disinfection_drinking_water.pdf#page=2"
CITE_KEYS = {
    ("bleeding", N + "Bleeding.html"): r"pressure",
    ("bleeding", WP): r"pressure",
    ("bleeding", "docs/medical/tccc/TCCC_Guidelines_2024-01-25.pdf"): r"2.3 inches|high (and|&) tight",
    ("bleeding", N + "Head_Injuries.html#Nosebleeds"): r"10 minutes",
    ("bleeding", NS + "Sangrado.html#Torniquetes"): r"torniquete",
    ("bleeding", NS + "Lesiones_de_la_cabeza.html#Sangrado_de_la_nariz"): r"10 minutos",
    ("bleeding", "docs/medical/fm_4-25.11_first_aid.pdf"): r"bleeding",
    ("bleeding", "docs/medical/emergency_war_surgery.pdf"): r"amputation",
    ("unconscious", N + "Breathing.html"): r"mouth.to.mouth|rescue breath",
    ("unconscious", WP): r"mouth.to.mouth|rescue breath",
    ("unconscious", NS + "P%C3%A9rdida_del_conocimiento.html"): r"conocimiento",
    ("unconscious", NS + "La_respiraci%C3%B3n.html#Respiraci.C3.B3n_de_boca_a_boca"): r"boca a boca",
    ("unconscious", NS + "No_tiene_pulso.html"): r"pulso",
    ("unconscious", "docs/medical/tccc/Airway_Management_in_Trauma.pdf"): r"airway",
    ("unconscious", N + "Loss_of_Consciousness.html"): r"unconscious",
    ("choking", N + "Chapter_3:_First_Aid.html"): r"chok",
    ("choking", WP): r"chok",
    ("choking", NS + "La_respiraci%C3%B3n.html#Cuando_se_atora_algo_en_la_garganta"): r"espalda",
    ("chest", N + "Heart_Attack.html"): (r"jaw", r"sweating"),
    ("chest", WP + "#page=28"): (r"heart attack", r"jaw", r"sweating"),
    ("chest", "docs/medical/tccc/Wartime_Thoracic_Injury.pdf"): r"seal",
    ("chest", NS + "Ataque_al_coraz%C3%B3n_(Infarto).html"): r"brazo",
    ("chest", NS + "Heridas_en_el_pecho_y_costillas_quebradas.html"): r"Pegue solo 3 lados",
    ("chest", MSF): r"respiratory",
    ("stroke", N + "Other_Heart_Problems.html#stroke"): r"3 hours",
    ("stroke", NS + "Otros_problemas_del_coraz%C3%B3n.html#stroke"): r"3 horas",
    ("stroke", NS + "Problemas_de_la_salud_de_los_ni%C3%B1os.html#Se.C3.B1as_de_peligro_y_causas_de_la_fiebre"):
        r"cuello r[ií]gido o fuerte dolor de cabeza",
    ("shock", N + "Shock.html"): r"warm",
    ("shock", WP): r"shock",
    ("shock", NS + "El_choque.html"): r"choque",
    ("shock", "docs/medical/tccc/Damage_Control_Resuscitation.pdf"): r"resuscitation",
    ("shock", HYPO): r"hypothermia",
    ("burns", WP + "#page=38"): [r"pour cool water over the burned skin for 15 to 30 minutes", r"avoid immersing the burn in cold water"],
    ("burns", WP + "#page=39"): r"If the blister has not opened, do not try to pop it",
    ("burns", N + "Burns.html"): (r"Never put ice, grease, fat", r"fluids", r"infection"),
    ("burns", "docs/medical/tccc/Burn_Care.pdf"): r"dry",
    ("burns", NS + "Quemaduras.html"): (r"15 a 30 minutos", r"Evite meter una quemadura peligrosa en agua fr[ií]a",
                                        r"Si la ampolla no est[aá] abierta, no intente abrirla"),
    ("burns", NS + "Quemaduras_por_productos_qu%C3%ADmicos.html"): r"qu[ií]mic",
    ("burns", MSF): r"\bburns\b",
    ("burns", WP): r"fluids",
    ("fire", W + "A_Community_Guide_to_Environmental_Health:Fire_Safety.html"):
        (r"DO NOT put water on a fire caused by cooking grease", r"sand"),
    ("fire", WS + "A_Community_Guide_to_Environmental_Health:Protecci%C3%B3n_contra_incendios.html"):
        r"No eche agua sobre llamas producidas por aceite o grasa",
    ("fire", "mirrors/ready_gov/www.ready.gov/es/incendios-en-el-hogar.html"): r"En menos de 30 segundos",
    ("fire", "mirrors/ready_gov/www.ready.gov/home-fires.html"): r"smoke alarm",
    ("fracture", N + "Broken_Bones,_Dislocations,_and_Sprains.html"): r"splint",
    ("fracture", WP): r"splint",
    ("fracture", NS + "Fracturas,_dislocaciones_y_esguinces.html"): r"tablilla",
    ("fracture", NS + "Fracturas,_dislocaciones_y_esguinces.html#Para_enyesar"): r"apretad",
    ("fracture", "docs/medical/tccc/Extremity_Compartment_Syndrome_Fasciotomy.pdf"): r"pain",
    ("wound", N + "Wounds.html"): r"clos",
    ("wound", WP): r"wound",
    ("wound", "docs/medical/tccc/Wound_Management_PFC.pdf"): r"irrigat",
    ("wound", NS + "Las_heridas.html"): r"agua",
    ("wound", NS + "Heridas_profundas.html"): r"herida",
    ("wound", NS + "Las_infecciones.html"): r"infecci",
    ("wound", NS + "Las_infecciones.html#Se.C3.B1as_de_infecci.C3.B3n"): r"ganglios",
    ("wound", NS + "Prevenir_y_manejar_las_complicaciones_de_la_diabetes.html"): r"l[ií]neas rojas que emanan de la lesi[oó]n",
    ("wound", "docs/medical/tccc/War_Wounds_Debridement_and_Irrigation.pdf"): r"debridement",
    ("wound", "docs/medical/icrc_first_aid_armed_conflicts.pdf"): r"wound",
    ("wound", MSF): r"infection",
    ("head", N + "Head_Injuries.html"): (r"24 hours", r"wake"),
    ("head", "docs/medical/tccc/TBI_Traumatic_Brain_Injury_PFC.pdf"): r"pupil",
    ("head", NS + "Lesiones_de_la_cabeza.html"): (r"24 horas", r"despi[eé]rt"),
    ("seizure", N + "Seizures,_Convulsions.html"): r"mouth",
    ("seizure", W + "Epilepsy_and_Seizures:First_aid_for_seizures.html"):
        (r"Do not put anything in their mouth", r"longer than 5 minutes"),
    ("seizure", W + "Epilepsy_and_Seizures:When_seizures_are_an_emergency.html"): r"5 minutes",
    ("seizure", NS + "Ataques,_convulsiones.html"): (r"Acu[eé]stela de costado", r"No sostenga"),
    ("seizure", WS + "Disabled_Village_Children:Que_hacer_cuando_a_un_ni%C3%B1o_le_da_un_ataque:Epilepsia.html"): r"No le ponga nada en la boca",
    ("seizure", MHGAP): r"epilepsy",
    ("diabetic", N + "Diabetic_Emergencies.html#Low_blood_sugar_.28hypoglycemia.29"): (r"honey under (his|her|the) tongue", r"insulin"),
    ("diabetic", N + "Loss_of_Consciousness.html"): r"Never give anything by mouth to a person who is unconscious",
    ("diabetic", NS + "Emergencias_diab%C3%A9ticas.html#Az.C3.BAcar_baja_en_la_sangre_.28hipoglicemia.29"):
        (r"miel debajo de (su|la) lengua", r"insulina"),
    ("diabetic", NS + "P%C3%A9rdida_del_conocimiento.html"): r"Nunca le d[eé] nada por la boca a una persona inconsciente",
    ("diabetic", N + "Diabetic_Emergencies.html#High_blood_sugar_.28hyperglycemia.29"): r"hyperglycemia",
    ("diabetic", N + "Chapter_21:_Diabetes.html"): r"diabetes",
    ("poison", N + "Poison.html"): (r"\bsalt\b", r"finger|throat"),
    ("poison", WP): r"poison",
    ("poison", NS + "Envenenamiento.html"): (r"\bsal\b", r"garganta"),
    ("poison", "docs/plant_id/amanita_death_cap/README.txt"): (r"liver", r"Español —"),
    ("poison", "docs/plant_id/README.txt"): r"Español",
    ("poison", MSF): r"intoxication",
    ("co", "mirrors/ready_gov/www.ready.gov/power-outages.html"): r"20 feet",
    ("co", W + "A_Community_Guide_to_Environmental_Health:Indoor_Air_Pollution.html#Carbon_monoxide_.28CO.29_poisoning"):
        r"carbon monoxide",
    ("co", WS + "A_Community_Guide_to_Environmental_Health:Contaminaci%C3%B3n_del_aire_interior.html"
           "#Envenenamiento_por_mon.C3.B3xido_de_carbono_.28CO.29"): r"mon[oó]xido de carbono",
    ("co", "mirrors/ready_gov/www.ready.gov/es/apagones.html"): r"20 pies",
    ("bite", N + "Stings_and_Bites.html"): (r"wrap the bitten area tightly", r"do not wrap the bite"),
    ("bite", N + "Medicines_for_Animal_Bites:_First_Aid.html"): r"rabies",
    ("bite", NS + "Picaduras_y_mordeduras.html#Mordeduras_de_v.C3.ADboras"): r"envuelva",
    ("bite", NS + "Heridas_profundas.html"): (r"Nunca cierre las heridas de mordeduras de animales",
                                             r"Las mordeduras de animales suelen infectarse"),
    ("bite", NS + "Medicinas_para_las_mordeduras_de_animales:Primeros_auxilios.html"): r"rabia",
    ("bite", WP): r"snake",
    ("allergy", N + "Allergy:_Mild_or_Severe_(Anaphylaxis).html"): r"thigh",
    ("allergy", NS + "Reacciones_al%C3%A9rgicas:_leves_o_graves.html"): r"epinefrina|adrenalina",
    ("allergy", MSF): r"anaphyla",
    ("fever", MSF + "#page=219"): (r"meningitis", r"neck"),
    ("fever", MSF): r"fever",
    ("fever", W + "Mpox.html"): r"rash",
    ("fever", "docs/medical/hesperian_where_there_is_no_doctor/en_nwtnd_2019_22a.pdf#page=10"): (r"dengue", r"paracetamol|acetaminophen"),
    ("fever", MSF + "#page=37"): r"dengue",
    ("fever", NS + "Problemas_de_la_salud_de_los_ni%C3%B1os.html#Meningitis"): r"cuello",
    ("fever", NS + "Las_infecciones.html"): r"infecci",
    ("fever", NS + "Infecci%C3%B3n_de_la_sangre_(sepsis).html"): r"sepsis",
    ("fever", NS + "Problemas_de_la_salud_de_los_ni%C3%B1os.html#Se.C3.B1as_de_peligro_y_causas_de_la_fiebre"): r"fiebre",
    ("fever", NS + "Problemas_de_la_salud_de_los_ni%C3%B1os.html#Fiebre_.28calentura.29"): r"fr[ií]o",
    ("fever", WS + "Viruela_s%C3%ADmica.html"): r"ampolla|grano",
    ("fever", WS + "A_Community_Guide_to_Environmental_Health:Fiebre_del_dengue_(fiebre_rompehuesos).html#Tratamiento"):
        (r"paracetamol, nunca ibuprofeno", r"ibuprofeno o paracetamol"),
    ("gut", N + "Chapter_15:_Belly_Pain,_Diarrhea,_and_Worms.html"): r"dehydrat",
    # FIXES #277 (r10 b3 N-03): the "can get worse fast and even kill" clause is the page intro, above «Señas de peligro»
    ("gut", NS + "Deshidrataci%C3%B3n.html"): [r"suero", r"puede empeorar r[aá]pidamente e incluso ser mortal"],
    ("gut", NS + "Diarrea.html"): r"diarrea",
    ("gut", NS + "Deshidrataci%C3%B3n.html#Se.C3.B1as_de_peligro"): r"hundid",
    ("gut", NS + "Diarrea.html#Se.C3.B1as_de_peligro"): r"sangre",
    ("gut", MSF): r"dehydration",
    ("gut", IMCI): (r"sunken", r"blood in (the )?stool"),
    ("belly", N + "Pain_in_the_Belly_or_Gut.html"): r"appendicitis",
    ("belly", NS + "Dolor_en_la_barriga_o_en_los_intestinos.html"): r"apendicitis",
    ("belly", MSF): r"abdom",
    ("belly", "docs/medical/who_surgical_care_district_hospital.pdf"): r"abdom",
    ("cold", HYPO): r"hypothermia",
    ("cold", N + "Cold_Emergencies.html"): (r"hypothermia", r"frostbite", r"\brub"),
    ("cold", NS + "Emergencias_causadas_por_el_fr%C3%ADo.html"): (r"No frote la piel", r"Es mejor dejar toda la zona congelada"),
    ("heat", N + "Heat_Emergencies.html"): (r"Rest in a cool place", r"Take off extra clothes",
                                            r"If not treated, heat exhaustion can worsen into heat stroke"),
    ("heat", NS + "Calambres_y_agotamiento_por_calor.html"): (r"Descansar en un lugar fresco", r"Si el agotamiento no se trata"),
    ("birth", OB): r"breech",
    ("birth", W + "Where_Women_Have_No_Doctor:Risks_and_Danger_Signs_during_Pregnancy.html#Bleeding_from_the_vagina"):
        (r"bleed", r"3 months|third month"),
    ("birth", OB + "#page=217"): r"resuscitation",
    ("birth", OB + "#page=190"): r"manual removal",
    ("birth", W + "A_Book_for_Midwives:What_to_do_for_the_baby:_The_birth_of_the_placenta.html"): r"placenta",
    ("birth", N + "After_the_Birth.html#Rub_the_womb"): r"\brub",
    ("birth", OB + "#page=175"): r"haemorrhage",
    ("birth", WS + "Un_libro_para_parteras.html"): r"parteras",
    ("birth", WS + "Where_Women_Have_No_Doctor:Riesgos_y_se%C3%B1as_de_peligro_durante_el_embarazo.html"
              "#Se.C3.B1as_de_peligro_durante_el_embarazo"): r"sangrado",
    ("birth", WS + "Where_Women_Have_No_Doctor:Riesgos_y_se%C3%B1as_de_peligro_durante_el_embarazo.html#Sangrado_vaginal"):
        r"sangrado",
    ("birth", WS + "Where_Women_Have_No_Doctor:Otros_tipos_de_problemas_de_sangrado.html"): r"primeros 3 meses",
    ("birth", NS + "Cap%C3%ADtulo_27:_Los_reci%C3%A9n_nacidos_y_el_amamantamiento.html"
              "#Si_el_beb.C3.A9_no_respira.2C_tiene_la_piel_azulada_o_el_cuerpo.C2.A0flojo"): r"respir",
    ("birth", WS + "A_Book_for_Midwives:Atender_al_beb%C3%A9.html#El_beb.C3.A9_no_respira"): r"respir",
    ("birth", NS + "El_nacimiento.html#La_placenta"): r"orin",
    ("birth", NS + "Despu%C3%A9s_del_parto.html#Sobe_la_matriz"): r"matriz",
    ("birth", W + "A_Book_for_Midwives.html"): r"midwi",
    ("birth", W + "HealthWiki.html"): r"Hesperian",
    ("birth", POCKET): r"newborn",
    ("child", IMCI): r"danger sign",
    ("child", NS + "Problemas_de_la_salud_de_los_ni%C3%B1os.html#Se.C3.B1as_de_peligro"): r"peligro",
    ("child", POCKET): r"children",
    ("child", N + "Chapter_28:_Caring_for_Children.html"): r"child",
    ("child", "docs/medical/hesperian_where_there_is_no_doctor/en_nwtnd_2011_28d.pdf"): r"child",
    ("tooth", DENT): r"dentist",
    ("tooth", DENT + "#page=55"): r"bone",
    ("tooth", W + "Where_There_Is_No_Dentist:A_Good_Diagnosis.html"): r"diagnos",
    ("tooth", WS + "Donde_no_hay_dentista.html"): r"dentista",
    ("tooth", WS + "Where_There_Is_No_Dentist:Por_qu%C3%A9_duelen_los_dientes_y_las_muelas.html"):
        r"La infecci[oó]n puede pasar del diente al hueso",
    ("eye", N + "Chapter_9:_Problems_with_the_Eyes_and_Seeing.html"): r"\beye",
    ("eye", "docs/medical/hesperian_where_there_is_no_doctor/en_nwtnd_2017_9.pdf"): r"\beye",
    ("eye", NS + "Emergencias_y_lesiones_de_los_ojos.html"): r"\bojo",
    # FIXES #277 (r10 b3 N-04): the chemical-flush time is the Hesperian page's, tied to the section that says it
    ("eye", N + "Eye_Emergencies_and_Injuries.html#Injuries_to_the_eye_from_chemicals"): r"at least 15 minutes to 30 minutes",
    ("eye", NS + "Emergencias_y_lesiones_de_los_ojos.html#Da.C3.B1o_en_los_ojos_por_sustancias_qu.C3.ADmicas"):
        r"por lo menos de 15 a 30 minutos",
    # FIXES #277 (r10 b5 F-M2-5): the English fever card's non-drug cooling step, from the page the Spanish card cites
    ("fever", N + "Health_Problems_of_Children.html#Fever"): (r"cool wet cloths", r"cool \(but not cold\) bath", r"fluids"),
    ("mind", "docs/medical/who_psychological_first_aid.pdf"): (r"listen", r"basic needs"),
    ("mind", N + "Mental_Health_Emergency.html"): r"Are you having thoughts of ending your life",
    ("mind", MHGAP + "#page=144"): (r"DO NOT leave the person alone", r"Remove means of self-harm"),
    ("mind", NS + "Emergencias_de_salud_mental.html"):
        r"Qu[eé]dese con la persona, o aseg[uú]rese de que amigos o familiares se queden con ella",
    ("mind", MHGAP): r"self-harm",
    ("mind", MHGAP + "#page=139"): r"self-harm|suicide",
    ("water", "mirrors/ready_gov/www.ready.gov/sites/default/files/2023-01/ready-gov_nuclear-detonation-safety_flyer1.pdf"):
        r"Water from your toilet tank \(not bowl\) and water heater is also safe",
    ("water", EPA2): r"You should not use water from toilet flush tanks or bowls",
    ("water", "docs/emergency_mgmt/fema_p530_earthquake_safety_at_home_2020.pdf#page=32"):
        r"Water heaters are also a source of emergency water",
    ("water", "mirrors/ready_gov/www.ready.gov/sites/default/files/2023-01/ready-gov_nuclear-detonation-safety_flyer_spanish.pdf"):
        r"inodoro",
    ("water", NS + "El_agua_y_la_salud.html"): r"agua",
    ("water", WS + "A_Community_Guide_to_Environmental_Health:Pozos_protegidos.html"): r"30 metros|30 m\b",
    ("water", "docs/medical/who_drinking_water_quality_4th_ed.pdf"): r"drinking",
    ("water", "docs/sanitation/sphere_handbook_2018.pdf#page=140"): r"30 m(etres|eters)?\b",
    ("water", "docs/sanitation/wedc_excreta_disposal_emergencies_field_manual_2007.pdf"): r"excreta",
}
_TEXT = {}


def cite_text(href, lib=LIB):
    """The words a reader finds behind href: one PDF page, a mirror page from its anchor on, or the whole file."""
    if href in _TEXT:
        return _TEXT[href]
    path, _, frag = href.partition("#")
    full = os.path.join(lib, urllib.parse.unquote(path))
    if not os.path.isfile(full):
        t = None
    elif path.lower().endswith(".pdf"):
        page = re.fullmatch(r"page=(\d+)", frag)
        r = subprocess.run(["pdftotext"] + (["-f", page.group(1), "-l", page.group(1)] if page else []) + [full, "-"],
                           capture_output=True, text=True)
        t = r.stdout if r.returncode == 0 else None
    else:
        s = open(full, encoding="utf-8", errors="replace").read()
        if frag:
            i = max(s.find(f'id="{frag}"'), s.find(f'id="{urllib.parse.unquote(frag)}"'))
            s = s[i:] if i >= 0 else None
        if s is not None and path.endswith((".html", ".htm")):
            s = H.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)\b.*?</\1>", " ", s, flags=re.S | re.I)))
        t = s
    _TEXT[href] = t = re.sub(r"\s+", " ", t) if t is not None else None
    return t


def card_cites(src):
    """(card, href) for every local file cited in a card's NOW, DEEPER and Spanish line."""
    out = []
    for c, blk in re.findall(r'<h2 id="([^"]+)" data-es="[^"]+">(.*?)(?=<h2 |<hr>)', src, re.S):
        for d in re.findall(r'<div class="(?:now|ref)">(.*?)</div>', blk, re.S):
            out += [(c, H.unescape(h)) for h in re.findall(r'<a [^>]*href="([^"]+)"', d)
                    if not h.startswith(("http:", "https:", "#", "search.html", "plants.html")) and not h.endswith("/")]
    return out


def cite_gaps(src, keys=CITE_KEYS, lib=LIB):
    found = card_cites(src)
    cites = set(found)
    gaps = [f"{c}: cite {h} has no key words in CITE_KEYS" for c, h in sorted(cites - set(keys))]
    gaps += [f"{c}: CITE_KEYS entry {h} matches no cite on the card" for c, h in sorted(set(keys) - cites)]
    for (c, h), rx in sorted(keys.items()):
        if (c, h) not in cites:
            continue
        t = cite_text(h, lib)
        if t is None:
            gaps.append(f"{c}: {h} is missing (file, PDF page or anchor)")
            continue
        if isinstance(rx, list) and len(rx) != found.count((c, h)):
            gaps.append(f"{c}: {h} is cited {found.count((c, h))} times, CITE_KEYS lists {len(rx)} clauses")
        gaps += [f"{c}: {h} does not hold /{r}/" for r in ((rx,) if isinstance(rx, str) else rx) if not re.search(r, t, re.I)]
    return gaps


def clauses(t):
    return [c for c in CLAUSE.findall(t.strip()) if not CLAUSE_SKIP.search(c)]


def twin_gaps(src, spans):
    """Per card: same number of <strong> clause labels, and every TWINS term in the English NOW has its Spanish term."""
    gaps, text = [], lambda h: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))
    for c, blk in re.findall(r'<h2 id="([^"]+)" data-es="[^"]+">(.*?)(?=<h2 |<hr>)', src, re.S):
        en = re.search(r'<div class="now">(.*?)</div>', ES_SPAN.sub("", blk), re.S).group(1)
        es = spans[c + "-es"]
        n_en = len(re.findall(r"<strong>", en)) - 1   # minus the NOW: label
        n_es = len(re.findall(r"<strong>", es)) - 1   # minus the En español: label
        if n_en != n_es:
            gaps.append(f"{c}: {n_en} English clause labels, {n_es} Spanish")
        c_en, c_es = clauses(text(en)), clauses(text(es))
        if len(c_en) > len(c_es):
            gaps.append(f"{c}: {len(c_en)} English situation clauses, {len(c_es)} Spanish: EN {c_en} ES {c_es}")
        gaps += [f"{c}: {a!r} has no Spanish {b!r}" for a, b in TWINS
                 if re.search(a, text(en), re.I) and not re.search(b, text(es), re.I)]
        deeper = re.search(r'<div class="ref">(.*?)</div>', blk, re.S)
        gaps += [f"{c}: DEEPER {a!r} has no Spanish {b!r}" for a, b in DEEPER_TWINS
                 if deeper and re.search(a, text(deeper.group(1)), re.I) and not re.search(b, text(es), re.I)]
    return gaps


def parse(src):
    src = re.sub(r"<!--.*?-->\s*", "", src, flags=re.S)
    spans = {k: v for k, v in ES_SPAN.findall(src)}
    assert not any("<span" in v for v in spans.values()), "nested span inside a Spanish line"
    cards = re.findall(r'<h2 id="([^"]+)" data-es="([^"]+)">', src)
    missing = [c for c, _ in cards if c + "-es" not in spans]
    assert not missing, f"cards without a Spanish line: {missing}"
    gaps = twin_gaps(src, spans)
    assert not gaps, "English clauses without a Spanish twin:\n  " + "\n  ".join(gaps)
    gaps = cite_gaps(src)
    assert not gaps, ("cites whose page does not hold the clause's key words:\n  " + "\n  ".join(gaps) +
                      ("\nThe triage cards cite these files as their evidence, so a library needs them: fetch docs/medical,"
                       " docs/sanitation, docs/emergency_mgmt, docs/plant_id and the hesperian and ready_gov mirrors"
                       " (sources.json \"content\")." if any("is missing" in g for g in gaps) else ""))
    return src, spans, cards


def en_v1(src, es_page):
    out = ES_SPAN.sub("", src)
    out = re.sub(r' data-es="[^"]*"', "", out)
    out = out.replace("<body>\n", "<body>\n" + SWITCH.format(idattr='id="es" ', href=es_page, l="es", t="Español") + "\n", 1)
    assert out.count('lang="es"') == 1, "Spanish left on an English page"   # the switch only
    return out


def es_v1(src, spans, cards, en_page, home):
    head = src.split("<body>", 1)[0].replace('<html lang="en">', '<html lang="es">')
    head = re.sub(r"<title>.*?</title>", "<title>EMERGENCIA — Guía de síntomas</title>", head)
    nav = "\n".join(f'<li><a href="#{c}">{t}</a></li>' for c, t in cards)
    body = "\n\n".join(
        f'<h2 id="{c}"><span id="{c}-es"></span>{t}</h2>\n'
        f'<div class="now"><strong>AHORA:</strong> {LABEL.sub("", spans[c + "-es"])}</div>\n'
        f'<div class="ref"><strong>EN INGLÉS:</strong> <a href="{en_page}#{c}" lang="en">la misma tarjeta en inglés, con más fuentes</a></div>'
        for c, t in cards)
    return f"""{head}<body>
{SWITCH.format(idattr="", href=en_page, l="en", t="English")}

<h1>Guía de síntomas — Empiece aquí</h1>

<div class="warn">
<strong>Qué es esta página:</strong> un mapa para llegar rápido al documento correcto. NO es consejo médico. {D2_ES} Niños: Harriet Lane (en inglés). Para dosis, nunca Wikipedia, nunca los manuales militares viejos.
Los archivos marcados <strong>HISTORICAL</strong> son de antes de 2010 y pueden traer prácticas viejas y dañinas: solo de fondo.
</div>

<nav><strong>Ir a:</strong>
<ul>
{nav}
</ul>
</nav>

<div class="now" id="es">
<strong>Cómo leer esta página:</strong> cada tarjeta tiene una línea <strong>AHORA</strong> (ábrala primero y actúe). Las páginas de Hesperian se abren también desde el disco; la Wikipedia médica necesita el servidor.
Libros en español: {LABEL.sub("", spans["es"])}
</div>

{body}

<hr>
<p><strong>¿No es una emergencia médica?</strong> Vuelva a la <a href="{home}">página principal en español</a>: comida, agua, luz, comunicaciones, reparaciones, mapas.</p>
<p style="color:#666;font-size:.85em">Escrito 2026-09, revisado 2026-10. Solo para orientarse: compruebe con las fuentes enlazadas. {D2_ES}</p>

</body>
</html>
"""


def lantern(v1, lang, home, other):
    """Restyle a v1 page into the Lantern shell. Content/links untouched: sections are lifted verbatim, only chrome is replaced."""
    es = lang == "es"
    nav_items = re.findall(r'<li><a href="#([^"]+)">([^<]+)</a></li>', v1)
    body = v1.split("</nav>", 1)[1].rsplit("<hr>", 1)[0]
    how = ""
    if es:   # the Spanish books box sits right after the jump list; it goes below the symptom grid
        how, body = re.match(r'\s*(<div class="now" id="es">.*?</div>)(.*)', body, re.S).groups()
        how = how.replace('class="now"', 'class="warn"', 1)
    body = body.replace('href="triage_v1.html#', 'href="triage.html#')
    now, deeper = ("AHORA", "EN INGLÉS") if es else ("NOW", "DEEPER")
    body = body.replace(f'<div class="now"><strong>{now}:</strong>', f'<div class="now"><span class="l-badge l-badge--danger">{now}</span> ')
    body = body.replace(f'<div class="ref"><strong>{deeper}:</strong>', f'<div class="ref"><span class="l-badge">{deeper}</span> ')
    body = re.sub(r'<h2 id="([^"]+)">', r'</section><section class="l-triage-section" id="\1"><h2>', body)
    body = body.replace("</section>", "", 1) + "</section>"
    dosing = '<p class="l-notice-dosing" style="margin-top:12px">' + (D2_ES if es else D2_EN) + "</p>"  # D2 wording, FIXES #150
    body = body.replace("</section>", dosing + "</section>")
    grid = "\n".join(f'<a href="#{a}">{t}</a>' for a, t in nav_items)
    # FIXES #254 (b3 B3-39): the print hint is plain words, not an onclick link, so it holds with JS off
    if es:
        switch = SWITCH.format(idattr="", href=other, l="en", t="English")
        intro = ('<h1>¿Qué está pasando?</h1>\n<p>Elija la situación. En cada tarjeta: <span class="l-badge l-badge--danger">AHORA</span> '
                 'actúe primero. Para imprimirla: Imprimir en el menú del navegador (en el teléfono: Compartir y luego Imprimir).</p>')
        box = (f'<div class="warn"><strong>No es consejo médico.</strong>\n{D2_ES} Niños: Harriet Lane (en inglés).\n'
               'Los archivos marcados HISTORICAL son de antes de 2010: solo de fondo.</div>')
        title, back, fwd = "Triaje de síntomas — Lantern", "← Página principal en español", ""
    else:
        switch = SWITCH.format(idattr='id="es" ', href=other, l="es", t="Español")
        intro = ('<h1>What is happening?</h1>\n<p>Pick the situation. Each section: <span class="l-badge l-badge--danger">NOW</span> act first,\n'
                 '<span class="l-badge">DEEPER</span> read when stabilized.\nTo print it: Print in the browser menu (on a phone: Share, then Print).</p>')
        box = ('<div class="warn"><strong>Not medical advice.</strong>\n' + D2_EN + ' Children: Harriet Lane.\n'
               'HISTORICAL-marked files are pre-2010 — background only.\n"WikiMed:" = open Kiwix → Wikipedia Medicine → search the quoted term.</div>')
        title, back, fwd = "Symptom Triage — Lantern", "← Library home", FWD.format(es=other) + "\n"
    out = f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
{favicon_html()}
<link rel="stylesheet" href="_app/fonts/fonts.css">
<link rel="stylesheet" href="_app/app.css">
<script src="_app/app.js" defer></script>
{fwd}<style>
 .now {{ background: var(--l-surface); border-left: 6px solid var(--l-danger);
   padding: 12px 16px; margin: 8px 0; border-radius: 0 8px 8px 0; font-size: 18px; }}
 .ref {{ background: var(--l-surface); border-left: 6px solid var(--l-ctl);
   padding: 12px 16px; margin: 8px 0; border-radius: 0 8px 8px 0; }}
 .warn {{ background: var(--l-surface); border-left: 6px solid var(--l-accent);
   padding: 12px 16px; margin: 8px 0; border-radius: 0 8px 8px 0; font-size: 13px;
   color: var(--l-text2); }}
</style>
</head>
<body>
<header class="l-header">
  {brand_html()}
  <button class="l-pill" data-role="status" onclick="lanternToggleTheme()"><span class="dot"></span>…</button>
</header>
<div class="l-wrap">
{switch}
{intro}

{box}

<nav class="l-symptoms" aria-label="{'Síntomas' if es else 'Symptoms'}">
{grid}
</nav>
{how}
{body}

<p style="margin:24px 0"><a href="{home}">{back}</a></p>
</div>
<!--TABBAR-->
{tabbar_html("", "triage_es.html", lang="es") if es else tabbar_html("", "triage.html")}
<!--/TABBAR-->
</body>
</html>
"""
    return resolve(out), out.count("l-triage-section"), len(nav_items)


def main():
    dst = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else LIB
    os.makedirs(dst, exist_ok=True)
    src, spans, cards = parse(open(SRC).read())
    # Spanish landing page (K4): es.html on the server; es_v1.html on the drive if K4 made one
    es_home = "es.html" if os.path.exists(os.path.join(LIB, "es.html")) else "index.html"
    es_home_v1 = "es_v1.html" if os.path.exists(os.path.join(LIB, "es_v1.html")) else es_home
    if es_home == "index.html":
        print("WARN: library/es.html missing; Spanish pages link home to index.html")
    pages = {"triage_v1.html": en_v1(src, "triage_es_v1.html"),
             "triage_es_v1.html": es_v1(src, spans, cards, "triage_v1.html", es_home_v1)}
    pages["triage.html"], n_en, nav_en = lantern(pages["triage_v1.html"], "en", "index.html", "triage_es.html")
    pages["triage_es.html"], n_es, nav_es = lantern(pages["triage_es_v1.html"], "es", es_home, "triage.html")
    assert n_en == n_es == len(cards) == nav_en == nav_es, (n_en, n_es, len(cards), nav_en, nav_es)
    for name, text in pages.items():
        with open(os.path.join(dst, name), "w") as f:
            f.write(text)
    print(f"cards={len(cards)} sections en={n_en} es={n_es} nav en={nav_en} es={nav_es} -> {dst}")


if __name__ == "__main__":
    main()
