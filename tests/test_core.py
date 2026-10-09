from app.main import executar


def test_executar(capsys):
    executar()

    resultado = capsys.readouterr()

    assert resultado.out.strip() == (
        "Aplicação DevOps funcionando!"
    )
