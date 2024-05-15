from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from openai import OpenAI
import requests
from bs4 import BeautifulSoup
import json
import pytz
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
SLACK_API_TOKEN = os.getenv('SLACK_API_TOKEN')

GEMINI=False
SLACK_CHANNEL = "#test-workspace"  # 投稿するSlackチャンネル名
FREQ = 24  # Frequency of invoking this bot in int


if GEMINI:
    import google.generativeai as genai
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-pro-latest')
else:
    client = OpenAI(
        api_key=OPENAI_API_KEY,
    )



def get_page_info_of_ak_blog():
    current_time_in_utc = datetime.now(pytz.timezone('UTC'))
    url = "https://huggingface.co/papers"
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")

    # time_tag = soup.find('time')['datetime']
    time_element = soup.find('time')
    month_span = time_element.find('span')
    day_span = month_span.find_next_sibling('span')
    # Combine the month and day
    date_string = f"{month_span.text} {day_span.text}"
    update_date = datetime.strptime(date_string, "%B %d").replace(year=current_time_in_utc.year)


    # update_date_in_utc = datetime.fromisoformat(time_tag.replace("Z", "+00:00"))
    last_check_time_in_utc = current_time_in_utc - timedelta(hours=FREQ)
    print(current_time_in_utc)
    print(update_date)
    print(last_check_time_in_utc)
    if current_time_in_utc.date() >= update_date.date() > last_check_time_in_utc.date():
        sections = soup.find_all('div', class_="SVELTE_HYDRATER contents")
        info = []
        for section in sections:
            data_props_string = section['data-props']
            data_props = json.loads(data_props_string)

            # Extract the 'dailyPapers' list from the data
            papers = data_props.get('dailyPapers', [])

            # Loop through each paper and print the title and summary
            for paper_entry in papers:
                paper = paper_entry.get('paper', {})
                title = paper.get('title', 'No Title available')
                summary = paper.get('summary', 'No Abstract available')
                info.append(f"Title: {title}\nAbstract: {summary}\n")
        return info
    else:
        return "NO update"



def summarize_and_translate(info):
    result_list = []
    for content in info:
        prompt = f"""論文のタイトルと概要を与えます。概要のみを日本語で要約し3行でまとめ、タイトルとともに以下のフォーマットで出力してください。
            
            出力例：
            【Octopus v4: Graph of language models】
            ・一般的な言語モデルは幅広い用途で効果的であるが、GPT-4などの高度な商用モデルは高価でエネルギー消費が大きい。
            ・オープンソースのコミュニティからは、特定の業界向けに最適化されたモデル（例：Llama3）が競争力を持ち、商用モデルを凌駕する場合もある。
            ・本論文は、複数のオープンソースモデルを統合し、各タスクに最適化された新しいアプローチ「Octopus v4」を紹介し、GitHubで公開している。

            {content}
            """
        if GEMINI:
            result_list = model.generate_content(prompt).text  # When you use gemini api
        else:
            response = client.chat.completions.create(
                        messages=[
                            {
                                "role": "user",
                                "content": prompt,
                            }
                        ],
                        model="gpt-4-0125-preview",
                    )
            result_list.append(response.choices[0].message.content)
    return result_list


# def main():
#     page_info = get_page_info_of_ak_blog()
#     if page_info == "NO update":
#         return
#
#     results = summarize_and_translate(get_page_info_of_ak_blog())
#
#     # メッセージの整形
#     message = "\nhttps://huggingface.co/papers に新しい論文が追加されました！\n\n"
#     for i, result in enumerate(results):
#         message += str(i + 1) + ".📄\n" + result + "\n\n\n"
#
#     try:
#         # Slackにメッセージを投稿
#         webclient = WebClient(token=SLACK_API_TOKEN)
#         response = webclient.chat_postMessage(
#             channel=SLACK_CHANNEL,
#             text=message
#         )
#         print(f"Message posted: {response['ts']}")
#     except SlackApiError as e:
#         print(f"Error posting message: {e}")


def main():
    page_info = get_page_info_of_ak_blog()
    if page_info == "NO update":
        #return
        message = "更新なし"
    else:
        results = summarize_and_translate(get_page_info_of_ak_blog())
        # メッセージの整形
        message = "\nhttps://huggingface.co/papers に新しい論文が追加されました！\n\n"
        for i, result in enumerate(results):
            message += str(i + 1) + ".📄\n" + result + "\n\n\n"

    try:
        # Slackにメッセージを投稿
        webclient = WebClient(token=SLACK_API_TOKEN)
        response = webclient.chat_postMessage(
            channel=SLACK_CHANNEL,
            text=message
        )
        print(f"Message posted: {response['ts']}")
    except SlackApiError as e:
        print(f"Error posting message: {e}")


if __name__ == "__main__":
    main()