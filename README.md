# Nginx-log-parser


1) Run docker file in interactive mode



    
        sudo docker run -it driver220v/log_parser
 
2) Run script: 



        python3 log_analyzer.py --folder=<store reort directory> --log=<gzipped log file>



3) for example:




        root@44644cde978f:/home/log_parser# python3 --folder=/home/log_parser/logs_saves --log=nginx-access-ui.log.gz

4) output:


        root@44644cde978f:/home/log_parser# ls -a 
    
            report1.html report2.html
    

