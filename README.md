# Virtual Air Mouse

---

## Γρήγορη εκκίνηση

```bash
# Δημιουργία venv + εγκατάσταση
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# Ο χρήστης πρέπει να ανήκει στην ομάδα uinput
sudo usermod -a -G uinput $USER
# (logout/login για να ενεργοποιηθεί)

# Εκτέλεση
venv/bin/python main.py
```

**Έλεγχοι:**
| Πλήκτρο | Λειτουργία |
|---------|------------|
| `m` | Ενεργοποίηση/Απενεργοποίηση κέρσορα |
| `q` | Έξοδος |

