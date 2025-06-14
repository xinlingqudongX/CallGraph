import Java from "frida-java-bridge";

// 辅助函数：获取Java堆栈信息
function getJavaStackTrace(): string {
    return Java.use('android.util.Log').getStackTraceString(Java.use('java.lang.Exception').$new());
}

if (Java.available) {
    Java.perform(() => {
        hookWhatsApp()
    });
} else {
    console.log("No Java VM in this process");
}

function hookWhatsApp() { 
    const LogClass = Java.use("com.whatsapp.util.Log");
    LogClass.level.value = 5;

    // 通用的日志处理方法
    function createLogHook(method: string, logType: string) {
        return {
            // 处理普通字符串日志
            string: function(str: string) {
                const stackTrace = getJavaStackTrace();
                send({
                    type: 'trace',
                    logType: 'stack_trace',
                    timestamp: new Date().toISOString(),
                    message: str,
                    data: {
                        method: method,
                        stackTrace: stackTrace
                    }
                });
                return this[method](str);
            },
            // 处理带异常的日志
            exception: function(str: string, th: any) {
                const stackTrace = getJavaStackTrace();
                send({
                    type: 'trace',
                    logType: 'stack_trace',
                    timestamp: new Date().toISOString(),
                    message: str,
                    data: {
                        method: method,
                        stackTrace: stackTrace,
                        exception: th.toString()
                    }
                });
                return this[method](str, th);
            }
        };
    }

    // 为每个日志级别创建hook
    const logHooks = {
        i: createLogHook('i', 'info'),
        d: createLogHook('d', 'debug'),
        e: createLogHook('e', 'error'),
        w: createLogHook('w', 'warn'),
        v: createLogHook('v', 'verbose')
    };

    // 应用所有hook
    Object.entries(logHooks).forEach(([method, hooks]) => {
        LogClass[method].overload('java.lang.String').implementation = hooks.string;
        LogClass[method].overload('java.lang.String', 'java.lang.Throwable').implementation = hooks.exception;
    });

    // Hook Log类的setLogLevel方法
    LogClass.setLogLevel.implementation = function() {
        this.level.value = 5;
    };
}