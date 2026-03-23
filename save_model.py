# ============================================================
# save_model.py — Run this ONCE to save trained KAN model
# Run from AD_LAB_ML_PROJECT folder AFTER PSO_KAN_fast.py
# ============================================================
# Instructions:
#   1. Open PSO_KAN_fast.py
#   2. Add these lines at the very END of the file:
#      exec(open("save_model.py").read())
#   OR run separately after training completes

import torch
import pickle
import os

# These variables come from PSO_KAN_fast.py after training
# Make sure final_model, scaler, best_params, layer_sizes are in scope

def save_kan_model(model, scaler, best_params, layer_sizes, threshold, save_dir="."):
    """Save KAN model weights and scaler to disk."""
    os.makedirs(save_dir, exist_ok=True)

    # Save model
    model_path = os.path.join(save_dir, "kan_model.pth")
    torch.save({
        "model_state_dict": model.state_dict(),
        "layer_sizes":      layer_sizes,
        "grid_size":        best_params["grid"],
        "spline_order":     best_params["order"],
        "dropout":          best_params["drop"],
        "threshold":        threshold,
        "best_params":      best_params,
    }, model_path)
    print(f"✅ Model saved: {model_path}")

    # Save scaler
    scaler_path = os.path.join(save_dir, "scaler.pkl")
    with open(scaler_path, "wb") as f:
        pickle.dump(scaler, f)
    print(f"✅ Scaler saved: {scaler_path}")

    return model_path, scaler_path


# ── ADD THIS TO END OF PSO_KAN_fast.py ────────────────────────
# After the line: _, final_model = train_kan(best, ...)
# Add:
#
# from save_model import save_kan_model
# save_kan_model(final_model, scaler, best, layer_sizes, thr, save_dir=".")
# ──────────────────────────────────────────────────────────────
