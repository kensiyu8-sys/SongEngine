"""SongEngine Desktop v0.3 entry point (also serves packaged background workers)."""
import sys

def main():
    if len(sys.argv)>1 and sys.argv[1]=="--worker":
        from worker import run
        return run(sys.argv[2])
    from ui import App
    app=App()
    if "--self-test-ui" in sys.argv:
        def test():
            try:
                app.self_test()
                print("UI smoke test passed.",flush=True)
            except Exception:
                import traceback
                traceback.print_exc()
                app.test_failed=True
            finally:app.destroy()
        app.after(200,test)
        app.mainloop()
        return 1 if getattr(app,"test_failed",False) else 0
    app.mainloop()
    return 0

if __name__=="__main__":
    sys.exit(main())
