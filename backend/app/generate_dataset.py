"""
generate_dataset.py — Synthetic Telecom Churn Dataset Generator

Generates a realistic dataset that exactly matches ChurnGuard AI's training schema.
Distributions mirror the classic Orange Telecom / BigML churn dataset.

Usage (run from inside the container):
    docker compose exec app python generate_dataset.py

Or on the host:
    python generate_dataset.py
"""

import os
import random

import numpy as np
import pandas as pd

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

N = 3333  # matches original Orange Telecom dataset size

STATES = [
    "AK","AL","AR","AZ","CA","CO","CT","DC","DE","FL","GA","HI","IA","ID",
    "IL","IN","KS","KY","LA","MA","MD","ME","MI","MN","MO","MS","MT","NC",
    "ND","NE","NH","NJ","NM","NV","NY","OH","OK","OR","PA","RI","SC","SD",
    "TN","TX","UT","VA","VT","WA","WI","WV","WY",
]

def generate_record(churn: bool) -> dict:
    """Generate one customer record. Churn=True customers have heavier usage patterns."""

    state = random.choice(STATES)
    account_length = int(np.random.normal(100, 40))
    account_length = max(1, min(243, account_length))
    area_code = random.choice([408, 415, 510])
    international_plan = "yes" if (random.random() < 0.42 if churn else random.random() < 0.09) else "no"
    voice_mail_plan = "yes" if random.random() < (0.09 if churn else 0.30) else "no"
    number_vmail_messages = int(np.random.poisson(8)) if voice_mail_plan == "yes" else 0

    # Churners use significantly more day minutes
    if churn:
        total_day_minutes = round(np.random.normal(206, 35), 1)
    else:
        total_day_minutes = round(np.random.normal(175, 40), 1)
    total_day_minutes = max(0.0, total_day_minutes)
    total_day_calls = int(np.random.normal(100, 20))
    total_day_calls = max(0, total_day_calls)
    total_day_charge = round(total_day_minutes * 0.17, 2)

    total_eve_minutes = round(np.random.normal(201, 35), 1)
    total_eve_minutes = max(0.0, total_eve_minutes)
    total_eve_calls = int(np.random.normal(100, 20))
    total_eve_calls = max(0, total_eve_calls)
    total_eve_charge = round(total_eve_minutes * 0.085, 2)

    total_night_minutes = round(np.random.normal(200, 35), 1)
    total_night_minutes = max(0.0, total_night_minutes)
    total_night_calls = int(np.random.normal(100, 20))
    total_night_calls = max(0, total_night_calls)
    total_night_charge = round(total_night_minutes * 0.045, 2)

    total_intl_minutes = round(np.random.normal(10, 3), 1)
    total_intl_minutes = max(0.0, total_intl_minutes)
    total_intl_calls = int(np.random.poisson(4))
    total_intl_charge = round(total_intl_minutes * 0.27, 2)

    # Churners call customer service more
    if churn:
        customer_service_calls = int(np.random.poisson(2.2))
    else:
        customer_service_calls = int(np.random.poisson(1.4))
    customer_service_calls = min(customer_service_calls, 9)

    return {
        "state": state,
        "account_length": account_length,
        "area_code": area_code,
        "international_plan": international_plan,
        "voice_mail_plan": voice_mail_plan,
        "number_vmail_messages": number_vmail_messages,
        "total_day_minutes": total_day_minutes,
        "total_day_calls": total_day_calls,
        "total_day_charge": total_day_charge,
        "total_eve_minutes": total_eve_minutes,
        "total_eve_calls": total_eve_calls,
        "total_eve_charge": total_eve_charge,
        "total_night_minutes": total_night_minutes,
        "total_night_calls": total_night_calls,
        "total_night_charge": total_night_charge,
        "total_intl_minutes": total_intl_minutes,
        "total_intl_calls": total_intl_calls,
        "total_intl_charge": total_intl_charge,
        "customer_service_calls": customer_service_calls,
        "churn": "yes" if churn else "no",
    }


def main():
    # ~14.5% churn rate — matches Orange Telecom dataset
    n_churn = int(N * 0.145)
    n_no_churn = N - n_churn

    records = (
        [generate_record(churn=True) for _ in range(n_churn)]
        + [generate_record(churn=False) for _ in range(n_no_churn)]
    )

    df = pd.DataFrame(records)
    df = df.sample(frac=1, random_state=SEED).reset_index(drop=True)  # shuffle

    os.makedirs("data", exist_ok=True)
    out = "data/train.csv"
    df.to_csv(out, index=False)

    print(f"[OK] Generated {len(df)} rows → {out}")
    print(f"     Churn rate: {df['churn'].eq('yes').mean():.1%}")
    print(f"     Columns: {list(df.columns)}")
    print("\nFirst 2 rows:")
    print(df.head(2).to_string())


if __name__ == "__main__":
    main()
