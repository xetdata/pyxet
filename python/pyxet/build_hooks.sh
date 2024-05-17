set -e
if [[ "$OSTYPE" == "darwin"* ]]; then
  clang -O2 -shared -o target/libhooksx86.so -target x86_64-apple-macos10.9 hooks/open_hook.c 
  clang -O2 -shared -o target/libhooksarm.so -target arm64-apple-macos11 hooks/open_hook.c 
  lipo -create -output target/libhooks.so target/libhooksx86.so target/libhooksarm.so
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
  cc hooks/open_hook.c -O2 -shared -o target/libhooks.so 
fi

cp target/libhooks.so pyxet/xtracelib/libhooks.so
