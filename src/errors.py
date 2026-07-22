import socket
import os.path
import time
import os

class Error:
    
    def __init__(self, log, acc_manager):
        self.log = log
        self.acc_manager = acc_manager

    def PortError(self, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("127.0.0.1", port))
        except:
            print("""Valorant Decloak güvenlik duvarı tarafından engelleniyor!!
            - Güvenlik duvarı ayarlarını kontrol edip programa izin verin / duvarı kapatın
            - Valorant Decloak'ı ve/veya VALORANT'ı yeniden başlatın, olmazsa bilgisayarı yeniden başlatın
            - İnternet bağlantınız yavaşsa config.json'daki cooldown değerini 0 veya 1'den büyük bir sayı yapmak yardımcı olabilir.
            - O da olmazsa config.json'daki port numarasını değiştirmeyi deneyin.
            - Yukarıdakilerin hiçbiri işe yaramazsa destek sunucusuna katılın.
            """)
            self.log("Port is being blocked by the firewall or in use by another application")
        sock.close()

    def LockfileError(self, path, ignoreLockfile=False):
        #ignoring lockfile is for when lockfile exists but it's not really valid, (local endpoints are not initialized yet)
        if os.path.exists(path) and ignoreLockfile == False:
            return True
        else:
            self.log("Lockfile does not exist, VALORANT is not open")
            self.acc_manager.start_valorant()
            
            while not os.path.exists(path):
                time.sleep(1)
            os.system('cls')
            return True
