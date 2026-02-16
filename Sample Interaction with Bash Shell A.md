# Sample Interaction with Ollama model

ollama run qwen3-30b-abliterated-custom

>>> Hello

(Wait for model to load and respond. Ignore response)

>>> /set parameter num_ctx 40960
Set parameter 'num_ctx' to '40960'

(Check ollama ps in another bash shell to see impact on CPU / GPU usage. Keep changing num_ctx until CPU = 0 and GPU = 100%)


(Save model so that the next time model is started, it uses the optimal context size.)

>>> /save qwen3-30b-abliterated-custom
Created new model 'qwen3-30b-abliterated-custom'

