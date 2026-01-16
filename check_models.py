
import google.generativeai as genai
import os
import streamlit as st

# APIキー取得
api_key = None
try:
    # ローカルのsecrets.tomlを読み込むためのダミー処理
    # 実際には環境変数か直接指定でテスト
    import toml
    secrets = toml.load(".streamlit/secrets.toml")
    api_key = secrets.get("GEMINI_API_KEY")
except:
    pass

if not api_key:
    # ユーザーが提供したキーを使用
    api_key = "AIzaSyCV6aOwIYpGkggLdHpJ31CS5c_6BIHGJzM"

if not api_key:
    print("API Key not found")
    exit()

print(f"Using API Key: {api_key[:5]}...")

try:
    genai.configure(api_key=api_key)
    print("Listing available models:")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"Error: {e}")
