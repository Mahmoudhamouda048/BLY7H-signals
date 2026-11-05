# === استبدل دالة ultimate_score كلها بده ===
def ultimate_score(df, sym, memory):
    try:
        last = float(df['close'].iloc[-1])
        prev = float(df['close'].iloc[-2])
        change = ((last - prev) / prev * 100) if prev else 0

        tech, has_fvg, has_ob, fvg_data, rec_low, rec_high, tech_r = calc_smc(df, last)
        liq, liq_r = calc_institutional(df, last)
        gann, gann_r = calc_gann(last)
        astro, astro_r = calc_astro()

        ai_bonus = 0
        ai_r = "جديد"
        if use_ai:
            vol_col = 'vol' if 'vol' in df.columns else 'volume'
            vs = float(df[vol_col].iloc[-1]) / df[vol_col].astype(float).mean()
            for pat in memory.get('patterns', []):
                if abs(vs - pat.get('vol', 2)) < 1.5:
                    ai_bonus = 5
                    ai_r = f"شبه {pat['name']}"
                    break

        total = tech + liq + gann + astro + ai_bonus
        total = min(99, int(total))

        bull_b = fvg_data.get('bull_b')
        bull_m = fvg_data.get('bull_m')
        bear_b = fvg_data.get('bear_b')
        bear_t = fvg_data.get('bear_t')
        bear_m = fvg_data.get('bear_m')

        # === تحديد النوع والدخول الصحيح ===
        if bull_b is not None and last >= bull_b and (last - bull_b) / last * 100 < 5:
            ptype = "PUMP"
            best = bull_m if bull_m else last * 0.994
            no_ret = bull_b * 0.985
        elif bear_b is not None and last <= bear_b and (bear_b - last) / last * 100 < 5:
            ptype = "DUMP"
            best = bear_m if bear_m else last * 1.006
            no_ret = bear_t * 1.015 if bear_t else last * 1.02
        else:
            ptype = "PUMP" if change >= -0.3 else "DUMP"
            if ptype == "PUMP":
                best = last * 0.994
                no_ret = rec_low * 0.985
            else:
                best = last * 1.006
                no_ret = rec_high * 1.015

        # === ستوب وهدف مضمونين صح ===
        if ptype == "PUMP":
            # لونج: ستوب تحت الالغاء، هدف فوق الدخول
            best = min(best, last * 0.998)  # لازم تحت السعر
            stop = no_ret * 0.994
            tp1 = best * 1.028
            tp2 = best * 1.065
            # تأكد الهدف فوق السعر الحالي
            if tp1 <= last: tp1 = last * 1.02
            if tp2 <= tp1: tp2 = tp1 * 1.03
        else:
            # شورت: ستوب فوق الالغاء، هدف تحت الدخول
            best = max(best, last * 1.002)  # لازم فوق السعر
            stop = no_ret * 1.006
            tp1 = best * 0.972
            tp2 = best * 0.935
            # تأكد الهدف تحت السعر الحالي
            if tp1 >= last: tp1 = last * 0.98
            if tp2 >= tp1: tp2 = tp1 * 0.97

        return {
            'symbol': sym, 'score': total, 'tech': tech, 'liq': liq, 'gann': gann, 'astro': astro,
            'ai_bonus': int(ai_bonus), 'type': ptype, 'price': round(last, 6),
            'change_1h': round(change, 2), 'best_entry': round(best, 6),
            'no_return_point': round(no_ret, 6), 'stop_loss': round(stop, 6),
            'TP1': round(tp1, 6), 'TP2': round(tp2, 6), 'has_fvg': has_fvg, 'has_ob': has_ob,
            'liq_reason': liq_r, 'gann_reason': gann_r, 'astro_reason': astro_r,
            'ai_reason': ai_r, 'tech_reason': tech_r
        }
    except Exception as e:
        return None
