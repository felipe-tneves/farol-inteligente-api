#Bibliotecas
from ast import For
from cgitb import reset
from queue import Empty
from unittest import result
from flask import Flask, Response, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
import mysql.connector
import numpy as np
import json
import torch
import datetime
import requests
import os

#Diretorio onde vai ficar os arquivos de upload
DIRETORIO = "C:\\Users\\Workspace\\Desktop\\Projects\\farol-inteligente-api\\files\\"

#Conexão com o banco de dados
app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATION'] = True
app.config[
    'SQLALCHEMY_DATABASE_URI'] = 'mysql://root:84268426aS$@localhost/tcc'

db = SQLAlchemy(app)


#Model da tabela transito
class Transito(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    qtd = db.Column(db.Integer)
    data = db.Column(db.String(100))
    hora = db.Column(db.String(100))
    clima = db.Column(db.String(300))
    endereco = db.Column(db.String(200))

#Função para formatar os valores em json
    def to_json(self):
        return {
            "id": self.id,
            "qtd": self.qtd,
            "data": self.data,
            "hora": self.hora,
            "clima": self.clima,
            "endereco": self.endereco
        }

#Yolo 
#Reconhecimento e contagem de veiculos 
def yolo(nome_arquivo):
    model = torch.hub.load('ultralytics/yolov5', 'yolov5s')

    print(nome_arquivo)
    imgs = DIRETORIO + nome_arquivo

    results = model(imgs)
    results.save()
    print(results)
    result_car = results.pandas().xyxy[0]

    df = pd.DataFrame(result_car, columns=["confidence", "name"])
    detected = df['name'].str.contains('bus|car')
    #pega a quantidade de elementos de um dataframe
    i = 0
    for object in detected:
        if object:
            i = i + 1
    return i


#Função para pegar a data e hora
def time_now():
    hora = datetime.datetime.now().strftime("%H:%M:%S")
    data = datetime.datetime.now().strftime("%Y-%m-%d")

    return [hora, data]


#Função para pegar o clima tempo
def climaTempo():
    token = "ee369bc12a04e11edc6af6b841af96e1"
    clima_url = "http://apiadvisor.climatempo.com.br/api/v1/weather/locale/3477/current?token=" + str(
        token)
    clima_response = requests.request("GET", clima_url)
    clima_retorno_req = json.loads(clima_response.text)
    data_clima = clima_retorno_req['data']

    return data_clima


#CRUD - GET (Apresenta todos os dados da API)
@app.route("/transito", methods=["GET"])
def seleciona_tudo():
    try:
        transito_objetos = Transito.query.all()
        print(transito_objetos)
        transito_json = [transito.to_json() for transito in transito_objetos]
        return transito_json
    except Exception as e:
        print(e)


#CRUD - GET by ID (Apresenta um dado especifico)
@app.route("/transito/<endereco>", methods=["GET"])
def seleciona_um(endereco):
    try:
        transito_objeto = Transito.query.filter_by(endereco=endereco).order_by(-Transito.id).first()
        transito_json = transito_objeto.to_json()
        return transito_json
    except Exception as e:
        print(e)


#CRUD - POST Simulação (Cadastra os dados referente ao transito - Simulação)
@app.route("/test", methods=["POST"])
def cadastro_test():
    body = request.get_json()
    try:

        transito = Transito(qtd=body["qtd"],
                            data=body["data"],
                            hora=body["hora"],
                            clima=body["clima"],
                            endereco=body["endereco"])

        db.session.add(transito)
        db.session.commit()

        return gera_response(201, "transito", transito.to_json(),
                             "Criado com sucesso")

    except Exception as e:
        print(e)
        return gera_response(400, "transito", {}, "Erro ao cadastrar")


#CRUD - UPDATE (Atualiza um dado especifico)
@app.route("/transito/<id>", methods=["PUT"])
def atualiza(id):
    transito_objeto = Transito.query.filter_by(id=id).first()
    body = request.get_json()

    try:
        if ('qtd' in body):
            transito_objeto.qtd = body['qtd']
        if ('data' in body):
            transito_objeto.data = body['data']
        if ('hora' in body):
            transito_objeto.hora = body['hora']
        if ('clima' in body):
            transito_objeto.clima = body['clima']
        if ('endero' in body):
            transito_objeto.endero = body['endero']

        db.session.add(transito_objeto)
        db.session.commit()
        return gera_response(200, "transito", transito_objeto.to_json(),
                             "Atualizado com sucesso")

    except Exception as e:
        print(e)
        return gera_response(400, "transito", {}, "Erro ao atualizar")


#CRUD - DELETE (Apaga um dado especifico)
@app.route("/transito/<id>", methods=["DELETE"])
def deleta(id):
    transito_objeto = Transito.query.filter_by(id=id).first()

    try:
        db.session.delete(transito_objeto)
        db.session.commit()
        return gera_response(200, "transito", transito_objeto.to_json(),
                             "Excluido com sucesso")

    except Exception as e:
        print(e)
        return gera_response(400, "transito", {}, "Erro ao deletar")


#Lista os arquivos (Imagens do transito) 
@app.route("/arquivos", methods=["GET"])
def lista_arquivos():
    arquivos = []

    for nome_do_arquivo in os.listdir(DIRETORIO):
        endereco_do_arquivo = os.path.join(DIRETORIO, nome_do_arquivo)

        if (os.path.isfile(endereco_do_arquivo)):
            arquivos.append(nome_do_arquivo)

    return jsonify(arquivos)


#Dowloads dos arquivos 
@app.route("/arquivos/<nome_do_arquivo>", methods=["GET"])
def get_arquivo(nome_do_arquivo):
    return send_from_directory(DIRETORIO, nome_do_arquivo, as_attachment=True)


#Upload de arquivo
#Cadastro de dados automatico no banco de dados
@app.route("/arquivos", methods=["POST"])
def post_arquivo():

    arquivo = request.files.get("meuArquivo")
    endereco = request.form["rua"]

    nome_do_arquivo = arquivo.filename
    arquivo.save(os.path.join(DIRETORIO, nome_do_arquivo))

    qtd = yolo(nome_do_arquivo)
    data_hora = time_now()
    clima_tempo = climaTempo()

    try:

        transito = Transito(qtd=int(qtd),
                            data=data_hora[1],
                            hora=data_hora[0],
                            clima=str(clima_tempo),
                            endereco=endereco)

        db.session.add(transito)
        db.session.commit()

        return gera_response(201, "transito", transito.to_json(),
                             "Criado com sucesso")

    except Exception as e:
        print(e)
        return gera_response(400, "transito", {}, "Erro ao cadastrar")


def gera_response(status, nome_do_conteudo, conteudo, mensagem=False):
    body = {}
    body[nome_do_conteudo] = conteudo

    if (mensagem):
        body["mensagem"] = mensagem

    return Response(json.dumps(body),
                    status=status,
                    mimetype="application/json")


if __name__ == "__main__":
    app.run(debug=True, port=8000)
