#!/usr/bin/env python3
"""
Bot de Copy Trading para Polymarket
Autor: juankaspain
Descripción: Monitoriza y replica trades de traders exitosos en Polymarket
"""

import requests
import time
import json
from datetime import datetime

# Configuración
TRADER_ADDRESS = ""  # PEGAR AQUÍ LA DIRECCIÓN DEL TRADER kch123
YOUR_CAPITAL = 1000  # Tu capital en USD
POLLING_INTERVAL = 30  # Segundos entre cada verificación
MODE = "monitor"  # monitor | execute

print("""  
╔══════════════════════════════════════════════════════════╗
║     BOT DE COPY TRADING - POLYMARKET                     ║
║     Monitoriza traders exitosos automáticamente          ║
╚══════════════════════════════════════════════════════════╝
""")

if not TRADER_ADDRESS:
    print("❌ ERROR: Debes configurar TRADER_ADDRESS")
    print("   Edita main.py y pega la dirección wallet del trader")
    exit(1)

print(f"🎯 Trader objetivo: {TRADER_ADDRESS}")
print(f"💰 Capital: ${YOUR_CAPITAL:,.2f}")
print(f"⏱️  Intervalo: {POLLING_INTERVAL}s")
print(f"🔧 Modo: {MODE.upper()}")
print("─" * 60)

previous_positions = {}
iteration = 0

while True:
    try:
        iteration += 1
        print(f"\n🔄 Iteración #{iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Obtener posiciones actuales del trader
        url = f"https://data-api.polymarket.com/positions"
        params = {
            'user': TRADER_ADDRESS,
            'sizeThreshold': 100,
            'limit': 50
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        current_positions = response.json()
        
        print(f"📊 Posiciones activas: {len(current_positions)}")
        
        if current_positions:
            # Mostrar top 5 posiciones por valor
            print("\n🏆 Top 5 posiciones por valor:")
            sorted_pos = sorted(current_positions, key=lambda x: x.get('currentValue', 0), reverse=True)[:5]
            
            for i, pos in enumerate(sorted_pos, 1):
                title = pos.get('title', 'Sin título')[:50]
                value = pos.get('currentValue', 0)
                pnl_pct = pos.get('percentPnl', 0)
                outcome = pos.get('outcome', 'N/A')
                
                pnl_emoji = "📈" if pnl_pct > 0 else "📉" if pnl_pct < 0 else "➖"
                print(f"{pnl_emoji} {i}. {title}")
                print(f"   └─ {outcome} | ${value:,.2f} | PnL: {pnl_pct:+.2f}%")
            
            # Detectar nuevas posiciones
            current_keys = {f"{p['conditionId']}_{p['outcome']}" for p in current_positions}
            previous_keys = set(previous_positions.keys())
            
            new_positions = current_keys - previous_keys
            
            if new_positions:
                print(f"\n🆕 Detectadas {len(new_positions)} NUEVAS posiciones:")
                for key in new_positions:
                    for pos in current_positions:
                        if f"{pos['conditionId']}_{pos['outcome']}" == key:
                            print(f"   ✨ {pos['title']}")
                            print(f"      └─ {pos['outcome']} @ {pos['avgPrice']:.2f}¢")
                            print(f"      └─ Tamaño: {pos['size']:,.0f} shares (${pos['initialValue']:,.2f})")
                            
                            if MODE == "execute":
                                print("      └─ ⚠️  MODO EXECUTE no implementado (requiere wallet)")
                            else:
                                print("      └─ ℹ️  Modo MONITOR - No se ejecuta trade")
            
            # Actualizar posiciones anteriores
            previous_positions = {f"{p['conditionId']}_{p['outcome']}": p for p in current_positions}
        
        else:
            print("⚠️  No se encontraron posiciones activas")
        
        print(f"\n⏳ Esperando {POLLING_INTERVAL} segundos...")
        time.sleep(POLLING_INTERVAL)
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de red: {e}")
        time.sleep(60)
    except KeyboardInterrupt:
        print("\n\n👋 Bot detenido por el usuario")
        break
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        time.sleep(60)
