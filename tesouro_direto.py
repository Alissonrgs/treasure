#!/usr/bin/env python3
import argparse
import matplotlib.pyplot as plt
import pandas as pd
import pyexcel
import requests

from bs4 import BeautifulSoup as bs
from datetime import datetime
from io import StringIO
from prettytable import PrettyTable

INFO = \
    "Histórico de preços e taxas (http://www.tesouro.gov.br/tesouro-direto-balanco-e-estatisticas)\n\n"\
    "Tesouro Selic (LFT)\n"\
    "Tesouro IPCA+ (NTN-B Principal)\n"\
    "Tesouro IPCA+ com Juros Semestrais (NTN-B)\n"\
    "Tesouro Prefixado (LTN)\n"\
    "Tesouro Prefixado com Juros Semestrais (NTN-F)\n"

URL = "http://www.tesouro.fazenda.gov.br/tesouro-direto-precos-e-taxas-dos-titulos"
URL_HISTORY = "http://sisweb.tesouro.gov.br/apex/f?p=2031:2:::::"
TREASURE_LIST = ["LFT", "LTN", "NTN-C", "NTN-B", "NTN-B Principal", "NTN-F"]
TREASURE_LINK = {treasure: {} for treasure in TREASURE_LIST}


parser = argparse.ArgumentParser(description='Tesouro Direto')
parser.add_argument(
    '-t', '--title',
    type=str, choices=TREASURE_LIST, help='Uma string representando o código do título')
parser.add_argument(
    '-i', '--info',
    action='store_true', help='Informações sobre o código de cada tesouro')
parser.add_argument(
    '-y', '--year',
    type=int, help="Um inteiro representando o ano")
parser.add_argument(
    '-d', '--download',
    action='store_true', help="Adicione para ser feito o download do gráfico"
)


def update_treasure_link():
    global TREASURE_LINK

    response = requests.get(URL_HISTORY)
    content = response.content.decode('utf-8')
    soup = bs(content, "html.parser")
    table = soup.find('div', class_="bl-body")

    year_list = [span.text[:4] for span in table.find_all('span')]
    year_index = 0
    for data in table:
        if data.name == 'br':
            continue
        if data.name == 'span':
            if year_list[year_index] in data.text:
                year = int(year_list[year_index])
                year_index += 1
        if data.name == 'a':
            href = data.get('href')
            TREASURE_LINK[data.text][year] = f"http://sisweb.tesouro.gov.br/apex/{href}"


def get_treasure_history_data(title, year, download):
    url = TREASURE_LINK[title][year]
    response = requests.get(url)
    book = pyexcel.get_book(file_type="xls", file_content=response.content)
    sheets = book.to_dict()

    print("Planihas Disponíveis:")
    for name, sheet_rows in sheets.items():
        print(f"{name} {sheet_rows[0][0]}: {sheet_rows[0][1]}")

    sheet_name = None
    while sheet_name not in sheets.keys():
        sheet_name = input("\nSelecione uma planilha: ")
        if sheet_name not in sheets.keys():
            print(f"A planilha {sheet_name} não foi encontrada!")

    print(book[sheet_name].content)

    df = pd.read_csv(StringIO(book[sheet_name].csv))
    df.rename(columns={
        'Vencimento': 'DATA',
        'Unnamed: 5': 'PU_BASE'
    }, inplace=True)
    df['DATA'] = pd.to_datetime(df['DATA'][1:], format='%d/%m/%Y')
    df['PU_BASE'] = pd.to_numeric(df['PU_BASE'][1:])
    df.sort_values('DATA', ascending=False, inplace=True)

    fig, ax = plt.subplots(figsize=(10, 8))
    fig.suptitle(sheet_name, fontsize=16)
    ax.plot(df['DATA'], df['PU_BASE'], 'b')
    ax.set_xlabel('DATA')
    ax.set_ylabel('PU BASE')
    ax.grid(True)

    if download:
        today = datetime.utcnow().strftime("%d_%m_%Y")
        sheet_name = sheet_name.replace(' ', '_')
        plt.savefig(f'{today}_{sheet_name}_PU_BASE.svg', format='svg', dpi=1200)
    plt.show()


def get_treasure_data():
    response = requests.get(URL)
    content = response.content.decode('utf-8')
    soup = bs(content, "html.parser")
    table = soup.find('table', class_='tabelaPrecoseTaxas')

    pretty_table = PrettyTable()

    field_names = [th.text.strip() for th in table.find('tr', class_='tabelaTitulo').find_all('th')]
    pretty_table.field_names = field_names

    treasure_title = [tr.find('td').text.strip() for tr in table.find_all('tr', class_='tituloprefixado')]
    treasure_index, treasure_size = 0, len(treasure_title)

    for tr in table.find_all('tr', class_='camposTesouroDireto'):
        td_list = [td.text.strip() for td in tr.find_all('td')]
        title = treasure_title[treasure_index]
        if treasure_index < treasure_size and title.split()[-1][:-1] in td_list[0]:
            pretty_table.add_row([title] + ['']*4)
            treasure_index += 1
        pretty_table.add_row(td_list)
    print(pretty_table)


if __name__ == "__main__":
    parse = parser.parse_args()

    if parse.info:
        print(INFO)
        get_treasure_data()
    else:
        title = parse.title
        year = parse.year
        download = parse.download
        if title and year:
            update_treasure_link()
            get_treasure_history_data(title, year, download)
        else:
            print("Você precisa inserir o nome do tesouro e o ano")
