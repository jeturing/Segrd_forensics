#!/usr/bin/env python3
"""
Script de prueba para análisis unificado de cuentas
Verifica integración de M365, Sparrow, Hawk y Sherlock
"""

import asyncio
import sys
import os
from pathlib import Path

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.account_analysis import (
    analyze_user_account,
    analyze_multiple_accounts,
    calculate_unified_risk,
    build_user_timeline
)


async def test_single_account():
    """Prueba análisis de una sola cuenta"""
    print("=" * 60)
    print("TEST 1: Análisis de cuenta individual")
    print("=" * 60)
    
    test_email = "admin@sinerlexrd.onmicrosoft.com"
    test_tenant = "3af2e132-c361-4467-9d8b-081f06630c12"
    test_case = "TEST-ACCOUNT-001"
    
    print(f"\n📧 Usuario: {test_email}")
    print(f"🏢 Tenant: {test_tenant}")
    print(f"📁 Caso: {test_case}")
    print("\n🔍 Ejecutando análisis completo...\n")
    
    try:
        result = await analyze_user_account(
            user_email=test_email,
            case_id=test_case,
            tenant_id=test_tenant,
            days_back=30,
            include_osint=True
        )
        
        print("✅ Análisis completado exitosamente\n")
        
        # Mostrar resumen
        print("📊 RESUMEN DEL ANÁLISIS:")
        print("-" * 60)
        
        if "risk_assessment" in result:
            risk = result["risk_assessment"]
            print(f"  Risk Score: {risk.get('risk_score', 0)}/100")
            print(f"  Risk Level: {risk.get('risk_level', 'unknown').upper()}")
            print(f"  Risk Factors: {risk.get('total_factors', 0)}")
            print()
        
        # M365 Analysis
        if "m365_analysis" in result and result["m365_analysis"].get("success"):
            m365 = result["m365_analysis"]
            print("  🔵 M365 Analysis:")
            print(f"     - Risky Sign-ins: {m365.get('risky_signins', 0)}")
            print(f"     - MFA Enabled: {'✅' if m365.get('mfa_enabled') else '❌'}")
            print(f"     - Risk Events: {m365.get('risk_events_count', 0)}")
            print()
        
        # Sparrow Analysis
        if "sparrow_analysis" in result and result["sparrow_analysis"].get("success"):
            sparrow = result["sparrow_analysis"]
            print("  🦅 Sparrow Analysis:")
            print(f"     - Indicators: {len(sparrow.get('indicators', []))}")
            print()
        
        # Mailbox Analysis
        if "mailbox_analysis" in result and result["mailbox_analysis"].get("success"):
            mailbox = result["mailbox_analysis"]
            print("  📧 Mailbox Analysis (Hawk):")
            print(f"     - Suspicious Rules: {len(mailbox.get('suspicious_rules', []))}")
            print(f"     - OAuth Apps: {len(mailbox.get('oauth_apps', []))}")
            print(f"     - Delegations: {len(mailbox.get('delegations', []))}")
            print()
        
        # OSINT Analysis
        if "osint_analysis" in result and result["osint_analysis"].get("success"):
            osint = result["osint_analysis"]
            print("  🔍 OSINT Analysis (Sherlock):")
            print(f"     - Profiles Found: {osint.get('profiles_found', 0)}")
            print(f"     - High-Risk Platforms: {osint.get('high_risk_platforms', 0)}")
            print()
        
        # Timeline
        if "timeline" in result and result["timeline"]:
            print(f"  📅 Timeline: {len(result['timeline'])} eventos")
            print("\n  Últimos 3 eventos:")
            for event in result["timeline"][:3]:
                print(f"     - [{event['timestamp']}] {event['event_type']}: {event['description']}")
            print()
        
        # Recommendations
        if "recommendations" in result and result["recommendations"]:
            print(f"  💡 Recomendaciones: {len(result['recommendations'])}")
            for rec in result["recommendations"][:3]:
                print(f"     - [{rec['priority'].upper()}] {rec['title']}")
            print()
        
        print("-" * 60)
        print(f"\n✅ TEST 1 COMPLETADO - Risk Score: {result.get('risk_assessment', {}).get('risk_score', 0)}/100\n")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_multiple_accounts():
    """Prueba análisis de múltiples cuentas"""
    print("=" * 60)
    print("TEST 2: Análisis de múltiples cuentas")
    print("=" * 60)
    
    test_emails = [
        "admin@sinerlexrd.onmicrosoft.com",
        "usuario1@sinerlexrd.onmicrosoft.com",
        "usuario2@sinerlexrd.onmicrosoft.com"
    ]
    test_tenant = "3af2e132-c361-4467-9d8b-081f06630c12"
    test_case = "TEST-BULK-001"
    
    print(f"\n📧 Usuarios: {len(test_emails)}")
    for email in test_emails:
        print(f"   - {email}")
    print(f"\n🏢 Tenant: {test_tenant}")
    print(f"📁 Caso: {test_case}")
    print("\n🔍 Ejecutando análisis masivo...\n")
    
    try:
        result = await analyze_multiple_accounts(
            user_emails=test_emails,
            case_id=test_case,
            tenant_id=test_tenant,
            days_back=30,
            include_osint=False  # Sin OSINT para prueba rápida
        )
        
        print("✅ Análisis masivo completado\n")
        
        # Mostrar resumen
        print("📊 RESUMEN DEL ANÁLISIS MASIVO:")
        print("-" * 60)
        print(f"  Cuentas Analizadas: {result.get('accounts_analyzed', 0)}/{len(test_emails)}")
        print(f"  Cuentas Exitosas: {result.get('accounts_analyzed', 0)}")
        print(f"  Cuentas Fallidas: {len(result.get('failed_accounts', []))}")
        print(f"  Risk Score Promedio: {result.get('average_risk_score', 0):.2f}/100")
        print()
        
        # Cuentas de alto riesgo
        high_risk = result.get('high_risk_accounts', [])
        if high_risk:
            print(f"  ⚠️  Cuentas de ALTO RIESGO: {len(high_risk)}")
            for acc in high_risk:
                print(f"     - {acc['email']}: {acc['risk_score']}/100 ({acc['risk_level']})")
            print()
        
        # Errores
        failed = result.get('failed_accounts', [])
        if failed:
            print(f"  ❌ Cuentas con ERROR: {len(failed)}")
            for fail in failed:
                print(f"     - {fail['email']}: {fail['error']}")
            print()
        
        print("-" * 60)
        print(f"\n✅ TEST 2 COMPLETADO - {result.get('accounts_analyzed', 0)} cuentas analizadas\n")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_risk_calculation():
    """Prueba cálculo de riesgo"""
    print("=" * 60)
    print("TEST 3: Cálculo de Risk Score")
    print("=" * 60)
    
    # Caso de prueba con datos simulados
    test_analysis = {
        "user_email": "test@empresa.com",
        "m365_analysis": {
            "success": True,
            "risky_signins": 3,
            "risk_events_count": 2,
            "mfa_enabled": False
        },
        "mailbox_analysis": {
            "success": True,
            "suspicious_rules": [
                {"rule": "Forward all"},
                {"rule": "Delete all"}
            ],
            "oauth_apps": [
                {"app": "SuspiciousApp1"},
                {"app": "SuspiciousApp2"},
                {"app": "SuspiciousApp3"}
            ]
        },
        "osint_analysis": {
            "success": True,
            "profiles_found": 5,
            "high_risk_platforms": 2
        }
    }
    
    print("\n📊 Datos de prueba:")
    print(f"  - Risky Sign-ins: 3")
    print(f"  - Risk Events: 2")
    print(f"  - MFA Enabled: False")
    print(f"  - Suspicious Rules: 2")
    print(f"  - OAuth Apps: 3")
    print(f"  - High-Risk Platforms: 2")
    print()
    
    try:
        risk_assessment = calculate_unified_risk(test_analysis)
        
        print("✅ Cálculo completado\n")
        print("📊 RESULTADO:")
        print("-" * 60)
        print(f"  Risk Score: {risk_assessment['risk_score']}/100")
        print(f"  Risk Level: {risk_assessment['risk_level'].upper()}")
        print(f"  Total Factors: {risk_assessment['total_factors']}")
        print()
        
        print("  Desglose de Puntos:")
        for factor in risk_assessment['risk_factors']:
            source = factor['source'].ljust(20)
            reason = factor['reason']
            points = factor['points']
            print(f"     {source}: +{points:2d} pts - {reason}")
        
        print("-" * 60)
        print(f"\n✅ TEST 3 COMPLETADO - Risk Level: {risk_assessment['risk_level'].upper()}\n")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Ejecuta todos los tests"""
    print("\n" + "=" * 60)
    print(" " * 15 + "ACCOUNT ANALYSIS TESTS")
    print("=" * 60 + "\n")
    
    results = []
    
    # Test 1: Single Account
    results.append(await test_single_account())
    await asyncio.sleep(2)
    
    # Test 2: Multiple Accounts
    results.append(await test_multiple_accounts())
    await asyncio.sleep(2)
    
    # Test 3: Risk Calculation
    results.append(await test_risk_calculation())
    
    # Resumen final
    print("\n" + "=" * 60)
    print("RESUMEN DE TESTS")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"\nTests ejecutados: {total}")
    print(f"Tests exitosos: {passed}")
    print(f"Tests fallidos: {total - passed}")
    
    if passed == total:
        print("\n✅ TODOS LOS TESTS PASARON")
    else:
        print(f"\n⚠️  {total - passed} TEST(S) FALLARON")
    
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
