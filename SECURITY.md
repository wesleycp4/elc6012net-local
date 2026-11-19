# Segurança

Este projeto controla uma **cerca elétrica e um alarme**. O protocolo da central não
autentica o servidor e o relay não tem senha própria.

## Uso seguro

- Mantenha a porta **9009**, o painel web do relay (`--web`) e o broker MQTT **só na
  rede local**. Não abra essas portas no roteador nem as publique por túnel.
- Use usuário e senha no broker MQTT: quem publica nos tópicos de comando controla a
  central.
- Ao apontar um domínio para o relay (opção A de [instalação](docs/instalacao.md)),
  use o **IP interno** e DNS sem proxy.
- Nunca publique capturas `.pcap`, dumps de flash ou a configuração da central: contêm
  o SSID e a senha do Wi-Fi e o código de acesso em texto claro.

## Relatar uma vulnerabilidade

Não abra issue pública. Use **Security → Report a vulnerability** no GitHub
(relato privado) com a descrição e, se possível, um passo a passo para reproduzir.
