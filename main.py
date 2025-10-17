# =============================================================================
# ### ARCHIVO: main.py ###
# =============================================================================
import customtkinter as ctk
from PIL import Image
from gui_manager import App
import os

class SplashScreen(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.overrideredirect(True)

        logo_path = "ecolora_logo.png"
        if os.path.exists(logo_path):
            pil_image = Image.open(logo_path)
            max_size = (400, 400)
            pil_image.thumbnail(max_size, Image.Resampling.LANCZOS)
            ctk_image = ctk.CTkImage(pil_image, size=pil_image.size)
            
            self.geometry(f"{pil_image.width}x{pil_image.height}")
            
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            x = (screen_width / 2) - (pil_image.width / 2)
            y = (screen_height / 2) - (pil_image.height / 2)
            self.geometry(f"+{int(x)}+{int(y)}")

            label = ctk.CTkLabel(self, text="", image=ctk_image)
            label.pack(expand=True, fill="both")
        
        # Después de 2.5 segundos, llama a la función para cerrar el splash
        self.after(2500, self.close_splash)

    def close_splash(self):
        self.master.deiconify() # Muestra la ventana principal que estaba oculta
        self.destroy()         # Destruye la ventana del splash

if __name__ == "__main__":
    # 1. Crear la instancia de la aplicación principal
    app = App()
    
    # 2. Ocultarla temporalmente
    app.withdraw()
    
    # 3. Crear y mostrar el splash screen, pasándole la app principal como master
    splash = SplashScreen(app)
    
    # 4. Iniciar el ÚNICO bucle de eventos principal.
    #    Este bucle manejará el splash y, cuando se cierre, continuará con la app.
    app.mainloop()