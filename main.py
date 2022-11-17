import json
import requests as rq
import pandas as pd
import streamlit as st
from datetime import datetime


def load_token():
    with open('kickflow_api.json') as api_f:
        kickflow_token = json.load(api_f)
        TOKEN = kickflow_token['token']
    return TOKEN


headers = {
        'Authorization': f'Bearer {load_token()}',
        'Content-Type': 'application/json'
    }


# httpリクエスト送信
def get_request(url, headers, params):
    response = rq.get(url, headers=headers, params=params)

    if response.status_code != 200:
        return response.status_code
    else:
        return response


@st.cache
def convert_df(df, index=True):
    return df.to_csv().encode('cp932')

def search_active_user():
    url = 'https://api.kickflow.com/v1/users'
    payload = {
        'perPage': 100,
        'status': 'active',
    }

    response = get_request(url, headers, payload)
    result = json.loads(response.text)

    df = pd.DataFrame(result)
    return df



# 未登録ユーザ一覧の取得
def search_unregistered_user():
    url = 'https://api.kickflow.com/v1/users'
    payload = {
        'page' : 1,
        'perPage': 25,
        'status': 'invited',
    }

    response = get_request(url, headers, payload)
    result = json.loads(response.text)

    df = pd.DataFrame(result)
    return df


# 使用中のワークフロー一覧取得
def get_workflow_list():
    url = 'https://api.kickflow.com/v1/workflows'
    payload = {
        'status': 'visible',
        'perPage': 100
    }
    response = get_request(url, headers, payload)
    result = json.loads(response.text)

    workflow_list = []
    for data in result:
        ticket_name = data['name']
        public_id = data['publicId']
        workflow_id = data['id']
        ticket_url = f'https://medias.kickflow.com/dashboard/mytickets/new?workflowId={public_id}'

        workflow_list.append([ticket_name, ticket_url, workflow_id])

    df = pd.DataFrame(workflow_list, columns=['ワークフロー名', 'URL', 'id'])
    return df


def get_date(from_time, until_time):
    from_time = datetime(from_time.year, from_time.month, from_time.day, 9)
    until_time = datetime(until_time.year, until_time.month, until_time.day, 8,59)
    return (from_time, until_time)


def get_invoice_ticket(id, from_time, until_time):
    from_time, until_time = get_date(from_time, until_time)
    url = 'https://api.kickflow.com/v1/tickets'
    payload = {
        'status': 'completed',
        'completedAtStart': from_time.isoformat(),
        'completedAtEnd': until_time.isoformat(),
        'workflowID': id
    }

    response = get_request(url, headers, payload)
    result = json.loads(response.text)

    df = pd.DataFrame(result)
    invoice_df = df[['id', 'ticketNumber', 'title', 'completedAt']]
    return invoice_df



def main():
    """
    アプリケーションのメイン機能
    :return:
    """
    st.header('Control Tool for kickflow')

    # sidebar
    st.sidebar.title('control panel')

    selector = st.sidebar.selectbox(
        'select box',
        ['選択してください', 'ワークフロー一覧', '未登録ユーザー', '支払申請']
        )
    btn = st.sidebar.button('データ表示')


    if selector == 'ワークフロー一覧':
        if btn:
            # ワークフロー一覧取得用の処理
            df_workflow = get_workflow_list()
            header_text = f'ワークフロー一覧 : <{df_workflow.shape[0]}件>'
            st.subheader(header_text)

            st.dataframe(df_workflow)
            workflow_list_csv = convert_df(df_workflow)

            st.download_button(
                label='[ ワークフロー一覧 ] as csv',
                data=workflow_list_csv,
                file_name='result_journal_EOM.csv',
                mime='text/csv',
            )

    elif selector == '未登録ユーザー':
        if btn:
            # 未登録ユーザ取得の処理
            # データ取得
            df = search_unregistered_user()
            header_text = f'招待済み未登録ユーザー : <{df.shape[0]}人>'
            st.subheader(header_text)

            # 必要カラムの抽出
            df_unregistered_user = df[['code', 'fullName', 'email', 'createdAt']]
            st.dataframe(df_unregistered_user)

    elif selector == '支払申請':
        from_date = st.sidebar.date_input('completedAtStart')
        until_date = st.sidebar.date_input('completedAtEnd')

        if btn:
            id_invoice = 'd40bd97c-a3eb-4f57-a4e7-6e1811e9474f'
            id_credit = '716f898b-78ad-4615-b1a1-28d9025635aa'
            id_direct_debit = 'f9c7115b-c5bb-4bbc-b739-63c694994d7b'
            id_capital_invest = 'c21c1590-b28a-480e-9bea-276a20fdb62a'

            try:
                df_invoice = get_invoice_ticket(id_invoice, from_date, until_date)
                header_text = f'支払申請（請求書） 完了チケット数 : <{df_invoice.shape[0]}件>'
                st.subheader(header_text)
                st.dataframe(df_invoice)

            except Exception:
                st.subheader('支払申請（請求書）')
                st.write('完了チケットはありません')

            try:
                df_invoice_credit = get_invoice_ticket(id_credit, from_date, until_date)
                header_text = f'支払申請（クレジット） 完了チケット数 : <{df_invoice_credit.shape[0]}件>'
                st.subheader(header_text)
                st.dataframe(df_invoice_credit)

            except Exception:
                st.subheader('支払申請（クレジット）')
                st.write('完了チケットはありません')

            try:
                df_invoice_direct_debit = get_invoice_ticket(id_direct_debit, from_date, until_date)
                header_text = f'支払申請（口座引落） 完了チケット数 : <{df_invoice_direct_debit.shape[0]}件>'
                st.subheader(header_text)
                st.dataframe(df_invoice_direct_debit)

            except Exception:
                st.subheader('支払申請（口座引落）')
                st.write('完了チケットはありません')

            try:
                df_invoice_capital_invest= get_invoice_ticket(id_capital_invest, from_date, until_date)
                header_text = f'支払申請（設備） 完了チケット数 : <{df_invoice_capital_invest.shape[0]}件>'
                st.subheader(header_text)
                st.dataframe(df_invoice_capital_invest)

            except Exception:
                st.subheader('支払申請（設備）')
                st.write('完了チケットはありません')

    else:
        if btn:
            st.sidebar.write('選択してください')

        st.write('右側のセレクトボックスより選択してください')


if __name__ == '__main__':
    main()
