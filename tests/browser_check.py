"""Real browser journey against isolated data. Never changes the user's database."""
import os, tempfile, subprocess, time, urllib.request, json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'test-results';OUT.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory() as data:
    env={**os.environ,'DATA_DIR':data,'APP_PASSWORD':'browser-test-only'}
    env.pop('OPENAI_API_KEY',None)
    proc=subprocess.Popen([str(ROOT/'.venv/bin/uvicorn'),'app.main:app','--host','127.0.0.1','--port','8011'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                urllib.request.urlopen('http://127.0.0.1:8011/api/health');break
            except Exception:time.sleep(.1)
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),args=['--no-sandbox'])
            desktop=browser.new_context(viewport={'width':1440,'height':1000})
            page=desktop.new_page();errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            def login(page):
                page.goto('http://127.0.0.1:8011');page.locator('#password').fill('browser-test-only');page.get_by_role('button',name='Entrar',exact=False).click();expect(page.get_by_role('heading',name='Un día con foco.')).to_be_visible()
            login(page)
            expect(page.locator('.focus-task')).to_contain_text('Probar la conciliación')
            page.screenshot(path=str(OUT/'desktop.png'),full_page=True)
            # Every view fits desktop without horizontal overflow.
            for view in ['clients','followups','reminders','settings','review','day']:
                page.goto('http://127.0.0.1:8011/#'+view);page.wait_for_timeout(100)
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),view
            page.locator('#capture-open').click();page.get_by_role('textbox',name='Contenido de la captura').fill('He hecho las pruebas de conciliación de GB Foods. Quedan dos casos con errores. Necesito revisarlos antes de dar la actualización del lunes')
            page.get_by_role('button',name='Guardar captura').click();expect(page.locator('#dialog')).not_to_be_visible()
            page.goto('http://127.0.0.1:8011/#review');expect(page.locator('.review-item')).to_contain_text('Revisar los dos casos con errores')
            page.get_by_role('button',name='Corregir',exact=True).click();expect(page.locator('#dialog')).to_be_visible();page.get_by_role('button',name='Guardar corrección').click();expect(page.locator('#dialog')).not_to_be_visible()
            page.get_by_role('button',name='Aceptar propuesta',exact=True).click();expect(page.get_by_role('heading',name='La bandeja está al día.')).to_be_visible()
            page.goto('http://127.0.0.1:8011/#matter/conciliation');expect(page.get_by_role('button',name='Revisar los dos casos con errores',exact=True)).to_be_visible()
            page.get_by_role('button',name='Revisar los dos casos con errores',exact=True).click();expect(page.locator('#dialog')).to_contain_text('Duración sin estimar');expect(page.locator('#dialog')).to_contain_text('He hecho las pruebas')
            page.locator('textarea[name=content]').fill('Necesito preparar una lista de los casos antes de revisar.');page.get_by_role('button',name='Guardar avance').click();expect(page.get_by_role('heading',name='Del apunte a la acción.')).to_be_visible()
            page.get_by_role('button',name='Aceptar propuesta').click();expect(page.get_by_role('heading',name='La bandeja está al día.')).to_be_visible()
            page.goto('http://127.0.0.1:8011/#matter/conciliation');page.get_by_role('button',name='Consultar este asunto').click();page.get_by_role('button',name='Consultar datos',exact=True).click();expect(page.locator('.assistant-result')).to_contain_text('dos casos con errores');expect(page.locator('.assistant-result')).not_to_contain_text('funciona correctamente')
            page.locator('#dialog-close').click()
            # A separately authenticated mobile device sees the same server data.
            mobile=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
            mp=mobile.new_page();mp.on('pageerror',lambda e:errors.append(str(e)));login(mp)
            for view in ['day','review','clients','followups','reminders','settings','matter/conciliation']:
                mp.goto('http://127.0.0.1:8011/#'+view);mp.wait_for_timeout(120)
                assert mp.evaluate('document.documentElement.scrollWidth<=innerWidth'),('mobile',view)
            expect(mp.get_by_role('button',name='Revisar los dos casos con errores',exact=True)).to_be_visible()
            mp.goto('http://127.0.0.1:8011/#day');mp.screenshot(path=str(OUT/'mobile.png'),full_page=True)
            mp.locator('#capture-open').click();expect(mp.get_by_role('textbox',name='Contenido de la captura')).to_be_visible();assert mp.locator('#dialog').bounding_box()['width']<=390;mp.keyboard.press('Escape');expect(mp.locator('#dialog')).not_to_be_visible()
            # Login survives a reload and all data remains present.
            page.reload();expect(page.get_by_role('button',name='Revisar los dos casos con errores',exact=True)).to_be_visible()
            assert not errors,errors
            session_cookie=next(c['value'] for c in desktop.cookies() if c['name']=='session')
            browser.close()
        # Restart server, database survives (not browser local storage).
        proc.terminate();proc.wait(timeout=5)
        from sqlite3 import connect
        with connect(str(Path(data)/'organizer.sqlite3')) as db:
            assert db.execute("SELECT COUNT(*) FROM tasks WHERE title='Revisar los dos casos con errores'").fetchone()[0]==1
            assert db.execute("SELECT status FROM tasks WHERE title='Probar la conciliación'").fetchone()[0]=='open'
        proc=subprocess.Popen([str(ROOT/'.venv/bin/uvicorn'),'app.main:app','--host','127.0.0.1','--port','8011'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for _ in range(50):
            try:
                request=urllib.request.Request('http://127.0.0.1:8011/api/state',headers={'Cookie':'session='+session_cookie})
                restored=json.load(urllib.request.urlopen(request));break
            except Exception:time.sleep(.1)
        else:raise AssertionError('Server did not restart')
        assert sum(t['title']=='Revisar los dos casos con errores' for t in restored['tasks'])==1
        print('PASS: browser capture → correction → acceptance → task context → progress → grounded summary; two devices; 7 responsive views; persisted database and session after server restart; no JavaScript errors.')
    finally:
        if proc.poll() is None:proc.terminate();proc.wait(timeout=5)
