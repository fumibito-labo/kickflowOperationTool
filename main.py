import json
# import matplotlib.pyplot as plt
import pandas as pd
import requests as rq
import streamlit as st
from datetime import datetime


def load_token():
    try:
        with open('api.json') as api_f:
            kickflow_token = json.load(api_f)
            TOKEN = kickflow_token['token']
    except Exception:
        TOKEN = st.secrets['TOKEN']
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


# ユーザー数(登録数)の取得
def get_total_user(per_page=50):
    url = 'https://api.kickflow.com/v1/users'
    payload = {
        'perPage': per_page,
    }
    response = get_request(url, headers, payload)
    result = response.headers
    # headerにあるトータル件数を抽出
    return result['Total']


# ユーザー一覧を取得
def get_users(max_page, per_page=50):
    cnt_list = [i + 1 for i in range(max_page)]
    url = 'https://api.kickflow.com/v1/users'
    df_user = pd.DataFrame(columns=['fullName', 'email', 'code', 'status'])
    for cnt in cnt_list:
        payload = {
            'page': cnt,
            'perPage': per_page,
        }

        response = get_request(url, headers, payload)
        result = json.loads(response.text)

        df_ = pd.DataFrame(result)
        df_ = df_[['fullName', 'email', 'code', 'createdAt', 'status']]
        df_user = pd.concat([df_user, df_], axis=0)
    return df_user


# アクティブユーザを取得
def get_active_users(df):
    active_user_df = df.query('status == "activated"')
    return active_user_df


# 未登録ユーザを取得
def get_unregistered_users(df):
    unregistered_user_df = df.query('status == "invited"')
    return unregistered_user_df


# メディアスユーザー抽出
def get_med_user(df):
    med_user_df = df[df['email'].str.contains('medias.co.jp')]
    med_user_count = med_user_df.shape[0]
    return med_user_count


def get_ccnc_user(df):
    ccnc_user_df = df[df['email'].str.contains('tac-net.co.jp')]
    ccnc_user_count = ccnc_user_df.shape[0]
    return ccnc_user_count

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
    until_time = datetime(until_time.year, until_time.month, until_time.day, 8, 59)
    return from_time, until_time


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
    invoice_df = df[['ticketNumber', 'title', 'id', 'completedAt']]
    return invoice_df


def main(per_page=50):
    """
    アプリケーションのメイン機能
    """
    st.header('Dash Board for "kickflow"')

    # sidebar
    st.sidebar.title('sidebar widget')

    selector = st.sidebar.selectbox(
        'select box',
        ['選択してください', 'ワークフロー', 'ユーザー情報', '支払申請']
    )
    btn = st.sidebar.button('データ表示')

    if selector == 'ワークフロー':
        if btn:
            # ワークフロー一覧取得用の処理
            df_workflow = get_workflow_list()
            st.metric('ワークフロー リスト', f'{df_workflow.shape[0]} 件')

            st.dataframe(df_workflow)
            workflow_list_csv = convert_df(df_workflow)

            st.download_button(
                label='[ ワークフロー 一覧 ] as csv',
                data=workflow_list_csv,
                file_name='workflowList.csv',
                mime='text/csv',
            )

    elif selector == 'ユーザー情報':
        st.subheader('アカウント状況')
        col1, col2, col3 = st.columns(3)
        # トータルユーザー数取得
        total_users = get_total_user()
        max_page = int(total_users) // per_page + 1
        col1.metric('登録ユーザー', f'{total_users}人')
        users = get_users(max_page)

        # アクティブユーザ一覧の取得
        active_user = get_active_users(users)
        col2.metric('アクティブユーザー', f'{active_user.shape[0]}人')

        # 未登録ユーザ取得の処理
        try:
            unregistered_user = get_unregistered_users(users)
            col3.metric('未登録ユーザー', f'{unregistered_user.shape[0]}人')
        except Exception:
            col3.metric('未登録ユーザー', '0人')

        if btn:
            st.write('---')
            st.subheader('ユーザー属性')
            container_user = st.container()
            col_1, col_2 = container_user.columns(2)
            med_count = get_med_user(users)
            ccnc_count = get_ccnc_user(users)
            col_1.metric('MEDIAS', f'{med_count}人')
            col_2.metric('CCNC', f'{ccnc_count}人')

            st.write('---')
            st.subheader('未登録ユーザーリスト')
            unregistered_filter_list = unregistered_user[['fullName', 'email', 'code', 'createdAt']]
            st.dataframe(unregistered_filter_list)

    elif selector == '支払申請':
        st.subheader('期間指定')
        container0 = st.container()
        container1 = st.container()
        container2 = st.container()
        container3 = st.container()
        container4 = st.container()
        container5 = st.container()

        col_from, col_until = container0.columns(2)
        from_date = col_from.date_input('From')
        until_date = col_until.date_input('To')

        col1, col2, col3, col4 = container1.columns(4)

        if btn:
            id_invoice = 'd40bd97c-a3eb-4f57-a4e7-6e1811e9474f'
            id_credit = '716f898b-78ad-4615-b1a1-28d9025635aa'
            id_direct_debit = 'f9c7115b-c5bb-4bbc-b739-63c694994d7b'
            id_capital_invest = 'c21c1590-b28a-480e-9bea-276a20fdb62a'

            try:
                df_invoice = get_invoice_ticket(id_invoice, from_date, until_date)
                col1.metric('請求書支払',  f'{df_invoice.shape[0]}件')
                with container2:
                    st.write('---')
                    st.write('#### 完了リスト: 請求書')
                    st.dataframe(df_invoice)

            except Exception:
                col1.metric('請求書支払',  '0件')
            try:
                df_invoice_credit = get_invoice_ticket(id_credit, from_date, until_date)
                col2.metric('クレジット支払', f'{df_invoice_credit.shape[0]}件')
                with container3:
                    st.write('---')
                    st.write('#### 完了リスト： クレジット')
                    st.dataframe(df_invoice_credit)

            except Exception:
                col2.metric('クレジット支払', '0件')
            try:
                df_invoice_direct_debit = get_invoice_ticket(id_direct_debit, from_date, until_date)
                col3.metric('口座引落支払', f'{df_invoice_direct_debit.shape[0]}件')
                with container4:
                    st.write('---')
                    st.write('#### 完了リスト： 口座引落')
                    st.dataframe(df_invoice_direct_debit)
            except Exception:
                col3.metric('口座引落支払', '0件')

            try:
                df_invoice_capital_invest = get_invoice_ticket(id_capital_invest, from_date, until_date)
                col4.metric('設備支払', f'{df_invoice_capital_invest.shape[0]}件>')
                with container5:
                    st.write('---')
                    st.write('#### 完了リスト： 設備')
                    st.dataframe(df_invoice_capital_invest)
            except Exception:
                col4.metric('設備支払', '0件')

    else:
        if btn:
            st.sidebar.write('選択してください')

        st.write('右側のセレクトボックスより選択してください')


if __name__ == '__main__':
    main()
