"""
デバイス判別モジュール
スマホ/PC判定のユーティリティ
"""
import streamlit as st


def is_mobile_device() -> bool:
    """
    モバイルデバイスかどうかを判定
    
    Streamlitではuser-agentを直接取得できないため、
    st.contextのheadersから推測する
    
    Returns:
        True if mobile device, False otherwise
    """
    try:
        # Streamlit Cloudではst.context.headersからUser-Agentを取得可能
        if hasattr(st, 'context') and hasattr(st.context, 'headers'):
            user_agent = st.context.headers.get('User-Agent', '').lower()
            mobile_keywords = [
                'mobile', 'android', 'iphone', 'ipad', 'ipod', 
                'webos', 'blackberry', 'windows phone'
            ]
            return any(keyword in user_agent for keyword in mobile_keywords)
    except:
        pass
    
    # フォールバック: セッション状態から判定（ユーザーが手動設定可能）
    return st.session_state.get('is_mobile', False)


def set_mobile_mode(is_mobile: bool):
    """
    モバイルモードを手動設定
    
    Args:
        is_mobile: True if mobile mode
    """
    st.session_state.is_mobile = is_mobile


def get_device_info() -> dict:
    """
    デバイス情報を取得
    
    Returns:
        dict with device info
    """
    try:
        if hasattr(st, 'context') and hasattr(st.context, 'headers'):
            user_agent = st.context.headers.get('User-Agent', '')
            return {
                'is_mobile': is_mobile_device(),
                'user_agent': user_agent[:100] if user_agent else 'Unknown'
            }
    except:
        pass
    
    return {
        'is_mobile': st.session_state.get('is_mobile', False),
        'user_agent': 'Unknown'
    }


def render_device_toggle():
    """
    デバイスモード切り替えUIを表示
    """
    current_mode = "スマホ" if is_mobile_device() else "PC"
    st.caption(f"現在のモード: {current_mode}")
    
    if st.checkbox("スマホモードを強制", value=st.session_state.get('is_mobile', False)):
        set_mobile_mode(True)
    else:
        set_mobile_mode(False)
