# ============================================================
# kan_predictor.py — Load saved KAN model, run predictions
# FIXED: Better prediction logic combining KAN + rule-based
# ============================================================
import torch
import torch.nn as nn
import numpy as np
import pickle
import os
import math
from dotenv import load_dotenv

load_dotenv()

# ── KAN MODEL DEFINITION ─────────────────────────────────────
class KANLinear(nn.Module):
    def __init__(self, in_f, out_f, grid_size=5, spline_order=3):
        super().__init__()
        self.spline_order = spline_order
        n_basis = grid_size + spline_order - 1
        grid = torch.linspace(-4.0, 4.0, grid_size + 1).unsqueeze(0)
        self.register_buffer("grid", grid)
        self.spline_weight = nn.Parameter(torch.randn(out_f, in_f, n_basis) * 0.05)
        self.base_weight   = nn.Parameter(torch.randn(out_f, in_f) * 0.1)
        self.spline_scaler = nn.Parameter(torch.ones(out_f, in_f) * 0.1)
        self.base_act      = nn.SiLU()

    def b_splines(self, x):
        x = x.unsqueeze(-1)
        x = torch.clamp(x, self.grid[:, 0].item(), self.grid[:, -1].item())
        g = self.grid.unsqueeze(0)
        bases = ((x >= g[:,:,:-1]) & (x < g[:,:,1:])).float()
        for k in range(1, self.spline_order + 1):
            ln = x - g[:,:,:-(k+1)]; ld = g[:,:,k:-1]  - g[:,:,:-(k+1)]
            rn = g[:,:,k+1:] - x;    rd = g[:,:,k+1:]  - g[:,:,1:-k]
            ld = torch.where(ld==0, torch.ones_like(ld), ld)
            rd = torch.where(rd==0, torch.ones_like(rd), rd)
            bases = (ln/ld)*bases[:,:,:-1] + (rn/rd)*bases[:,:,1:]
        return bases

    def forward(self, x):
        base_out   = self.base_act(x) @ self.base_weight.T
        splines    = self.b_splines(x)
        scaled_w   = self.spline_weight * self.spline_scaler.unsqueeze(-1)
        spline_out = torch.einsum("bin,oin->bo", splines, scaled_w)
        return base_out + spline_out


class KAN(nn.Module):
    def __init__(self, sizes, grid_size=5, spline_order=3, dropout=0.2):
        super().__init__()
        self.layers = nn.ModuleList()
        self.bns    = nn.ModuleList()
        self.acts   = nn.ModuleList()
        self.drops  = nn.ModuleList()
        for i in range(len(sizes)-1):
            self.layers.append(KANLinear(sizes[i], sizes[i+1], grid_size, spline_order))
            if i < len(sizes)-2:
                self.bns.append(nn.BatchNorm1d(sizes[i+1]))
                self.acts.append(nn.LeakyReLU(0.1))
                self.drops.append(nn.Dropout(dropout))

    def forward(self, x):
        for i, layer in enumerate(self.layers):
            x = layer(x)
            if i < len(self.layers)-1:
                x = self.bns[i](x)
                x = self.acts[i](x)
                x = self.drops[i](x)
        return x


def rule_based_score(data: dict) -> float:
    """
    Rule-based fraud scoring based on dataset patterns.
    Combines with KAN model output for better accuracy.
    Score range: 0.0 to 1.0
    """
    score = 0.0

    amt        = float(data.get("amt", 0))
    trans_hour = int(data.get("trans_hour", 12))
    trans_day  = int(data.get("trans_day", 0))
    city_pop   = float(data.get("city_pop", 100000))
    category   = str(data.get("category", "")).lower()
    distance   = float(data.get("distance_km", 0) or 0)
    is_night   = int(data.get("is_night", 0))
    is_weekend = int(data.get("is_weekend", 0))

    # Amount scoring (fraud transactions tend to be larger)
    if amt > 1000:   score += 0.30
    elif amt > 500:  score += 0.20
    elif amt > 200:  score += 0.10
    elif amt < 5:    score += 0.05   # very small amounts also suspicious

    # Distance scoring (fraud = large distances)
    if distance > 5000:   score += 0.35
    elif distance > 1000: score += 0.25
    elif distance > 500:  score += 0.15
    elif distance > 100:  score += 0.05

    # Time scoring (fraud peaks at night)
    if trans_hour >= 22 or trans_hour <= 4:
        score += 0.15
    elif trans_hour >= 20 or trans_hour <= 6:
        score += 0.08

    # Weekend scoring
    if trans_day in [0, 6]:  # Sunday or Saturday
        score += 0.05

    # Category scoring (high risk categories from dataset)
    high_risk_cats = ["misc_net", "shopping_net", "grocery_net"]
    if category in high_risk_cats:
        score += 0.10

    # City population scoring (fraud more common in small cities)
    if city_pop < 1000:    score += 0.10
    elif city_pop < 10000: score += 0.05

    return min(score, 1.0)


class KANPredictor:
    def __init__(self):
        self.model      = None
        self.scaler     = None
        self.threshold  = 0.5
        self.device     = torch.device("cpu")
        self.is_loaded  = False
        self._load_model()

    def _load_model(self):
        BASE_DIR = os.path.dirname(__file__)
        model_path  = os.path.join(BASE_DIR, "kan_model.pth")
        scaler_path = os.path.join(BASE_DIR, "scaler.pkl")

        try:
            with open(scaler_path, "rb") as f:
                self.scaler = pickle.load(f)

            checkpoint   = torch.load(model_path, map_location=self.device)
            layer_sizes  = checkpoint["layer_sizes"]
            grid_size    = checkpoint["grid_size"]
            spline_order = checkpoint["spline_order"]
            dropout      = checkpoint["dropout"]
            self.threshold = 0.5  # use 0.5 for combined score

            self.model = KAN(layer_sizes, grid_size, spline_order, dropout)
            self.model.load_state_dict(checkpoint["model_state_dict"])
            self.model.eval()

            # Pre-warm
            print("Pre-warming KAN model...")
            n_features = layer_sizes[0]
            dummy = np.zeros((1, n_features), dtype=np.float32)
            dummy_scaled = self.scaler.transform(dummy)
            x_dummy = torch.FloatTensor(dummy_scaled).to(self.device)
            with torch.inference_mode():
                _ = self.model(x_dummy)

            self.is_loaded = True
            print(f"✅ KAN model loaded | Architecture: {layer_sizes} | Threshold: {self.threshold}")
            print(f"✅ Model pre-warmed and ready!")

        except Exception as e:
            print(f"⚠️  Model not loaded: {e}")
            self.is_loaded = False

    def preprocess_input(self, data: dict) -> np.ndarray:
        amt        = float(data.get("amt", 0))
        trans_hour = int(data.get("trans_hour", 12))
        trans_day  = int(data.get("trans_day", 0))
        trans_month= int(data.get("trans_month", 1))
        trans_year = int(data.get("trans_year", 2024))

        lat1 = float(data.get("lat", 0))
        lon1 = float(data.get("long", 0))
        lat2 = float(data.get("merch_lat", 0))
        lon2 = float(data.get("merch_long", 0))

        if data.get("distance_km") is not None and float(data["distance_km"]) > 0:
            distance_km = float(data["distance_km"])
        else:
            R = 6371
            la1,lo1,la2,lo2 = map(math.radians,[lat1,lon1,lat2,lon2])
            a = math.sin((la2-la1)/2)**2 + math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
            distance_km = R * 2 * math.asin(math.sqrt(max(0, a)))

        # Store distance back for rule-based scoring
        data["distance_km"] = distance_km

        amt_log      = math.log1p(amt)
        amt_per_hour = amt / (trans_hour + 1)
        is_night     = int(data.get("is_night",
                           1 if (trans_hour >= 22 or trans_hour <= 5) else 0))
        is_weekend   = int(data.get("is_weekend",
                           1 if trans_day >= 5 else 0))

        category_map = {
            "grocery_pos":0,"shopping_net":1,"misc_net":2,"gas_transport":3,
            "grocery_net":4,"shopping_pos":5,"misc_pos":6,"food_dining":7,
            "personal_care":8,"health_fitness":9,"travel":10,"kids_pets":11,
            "home":12,"entertainment":13,"education":14
        }
        gender_map = {"M":0,"F":1,"m":0,"f":1}

        features = [
            amt,
            float(data.get("cc_num", 0)),
            category_map.get(str(data.get("category","misc_net")).lower(), 2),
            gender_map.get(str(data.get("gender","M")), 0),
            float(data.get("city_pop", 100000)),
            float(hash(str(data.get("job","unknown"))) % 1000),
            float(hash(str(data.get("merchant","unknown"))) % 1000),
            trans_hour, trans_day, trans_month, trans_year,
            distance_km, amt_log, amt_per_hour, is_night, is_weekend,
            float(hash(str(data.get("state","CA"))) % 50),
        ]
        return np.array(features, dtype=np.float32).reshape(1, -1)

    def predict(self, data: dict) -> dict:
        features = self.preprocess_input(data)

        # ── KAN model score ───────────────────────────────────
        if self.is_loaded and self.scaler:
            features_scaled = self.scaler.transform(features)
            x = torch.FloatTensor(features_scaled).to(self.device)
            with torch.inference_mode():
                kan_prob = torch.sigmoid(self.model(x)).item()
        else:
            kan_prob = 0.5

        # ── Rule-based score ──────────────────────────────────
        rule_prob = rule_based_score(data)

        # ── Combined score: 50% KAN + 50% rules ──────────────
        # This compensates for limited training data
        combined_prob = (kan_prob * 0.3) + (rule_prob * 0.7)

        print(f"  KAN score: {kan_prob:.4f} | Rule score: {rule_prob:.4f} | Combined: {combined_prob:.4f}")

        prediction = "FRAUD" if combined_prob >= self.threshold else "SAFE"
        confidence = "HIGH"   if abs(combined_prob - self.threshold) > 0.2 else \
                     "MEDIUM" if abs(combined_prob - self.threshold) > 0.1 else "LOW"
        risk_level = "CRITICAL" if combined_prob >= 0.9 else \
                     "HIGH"     if combined_prob >= 0.7 else \
                     "MEDIUM"   if combined_prob >= 0.4 else "LOW"

        amt        = float(data.get("amt", 0))
        trans_hour = int(data.get("trans_hour", 12))
        distance   = float(data.get("distance_km", 0) or 0)
        is_night   = int(data.get("is_night", 0) or
                        (1 if trans_hour >= 22 or trans_hour <= 5 else 0))
        is_weekend = int(data.get("is_weekend", 0) or 0)

        risk_factors = {
            "amount_risk":   round(min(1.0, amt / 5000), 3),
            "time_risk":     round(0.8 if is_night else 0.2, 3),
            "distance_risk": round(min(1.0, distance / 2000), 3),
            "weekend_risk":  round(0.6 if is_weekend else 0.2, 3),
        }

        return {
            "fraud_probability": round(combined_prob, 4),
            "prediction":        prediction,
            "confidence":        confidence,
            "threshold":         self.threshold,
            "risk_level":        risk_level,
            "risk_factors":      risk_factors,
        }


# Singleton
predictor = KANPredictor()
