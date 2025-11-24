import base64
from http import client
from openai import OpenAI

# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


# 一般的なメインファイルの実装をお願い致します。

def main():
    client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
    # Path to your image
    image_path = "C:\\github\\billing-ocr\\請求書サンプル.png"

    # Getting the Base64 string
    base64_image = encode_image(image_path)
    response = client.responses.create(
    model="gpt-4.1",
    input=[
        {
            "role": "user",
            "content": [
                { "type": "input_text", "text": "この画像を読み取ってjson形式にしてください。/n明細部分は配列としてください。/nヘッダー部分/nキー：件名/nキー：支払金額/nキー：請求日/nキー：請求金額合計/n明細部分/nキー：適用/nキー：数量/nキー：単位/nキー：単価/nキー：金額"},
                {
                    "type": "input_image",
                    "image_url": f"data:image/jpeg;base64,{base64_image}",
                },
            ],
        }
    ],
    )
    # OPENAI APIを使用した処理をここに記述します。
    print(response.output_text)
if __name__ == "__main__":
    main()
