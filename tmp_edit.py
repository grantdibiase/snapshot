from pathlib import Path

p = Path(r"c:\Users\Grant DiBiase\snapshot\backend\main.py")
text = p.read_text(encoding='utf-8')
old = """    except Exception as e:
        print(f\"AUTH ERROR: {str(e)}\")
        import traceback
        traceback.print_exc()
        return RedirectResponse(
            url=f\"http://localhost:3000/confirm?auth=error&message={str(e)}\"\n        )
"""
new = """    except Exception as e:
        print(f\"AUTH ERROR: {str(e)}\")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={\"status\": \"error\", \"detail\": str(e)}
        )
"""
if old not in text:
    raise SystemExit('old block not found')
text = text.replace(old, new)
p.write_text(text, encoding='utf-8')
print('patched')
