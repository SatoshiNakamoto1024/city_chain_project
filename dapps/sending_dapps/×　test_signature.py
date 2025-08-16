import pytest
import sys

sys.path.append(r"D:\city_chain_project\ntru\dilithium-py\src")
from dilithium_py.dilithium.dilithium import Dilithium  # Dilithium モジュール
from dilithium_py.polynomials.polynomials import (
    PolynomialRingDilithium,
    PolynomialDilithium,
    PolynomialDilithiumNTT,
)
from dilithium_py.modules.modules_generic import (
    Matrix,
    ModuleDilithium,
    MatrixDilithium,         # 両対応: NTT/Classic混在もOK
)
from dilithium_py.modules.modules import (
    MatrixDilithiumClassic,  # 全要素が PolynomialDilithium
    MatrixDilithiumNTT,     # 全要素が PolynomialDilithiumNTT
)
from dilithium_py.dilithium.default_parameters import Dilithium2


# parent のインスタンスを作成
parent = PolynomialRingDilithium()


@pytest.fixture
def shared_ring():
    return PolynomialRingDilithium(q=8380417)


def test_dilithium_signature():
    """
    NTT ポリを生成して MatrixDilithiumNTT でテストする例。
    """
    # 1. PolynomialRingDilithium
    parent = PolynomialRingDilithium(q=8380417, n=256, root_of_unity=1753)
    print(f"Parent ID: {id(parent)}")
    print(f"DEBUG: parent.ntt_zetas = {parent.ntt_zetas[:10]}")

    parameter_set = {
        "d": 14,
        "k": 4,
        "l": 4,
        "eta": 2,
        "tau": 39,
        "omega": 80,
        "gamma_1": 131072,  # 公式
        "gamma_2": 95232,    # 公式
        "beta": 196,          # 論文推奨値
    }

    # 2. ModuleDilithium インスタンス
    module = ModuleDilithium(q=8380417)

    # 3. ダミーの NTT ポリデータ作成（PolynomialDilithiumNTT）
    data_ntt = [
        [
            PolynomialDilithiumNTT(
                parent=parent,
                coeffs=[(i * 100 + j) % parent.q for j in range(parent.n)]
            )
            for j in range(4)
        ]
        for i in range(4)
    ]

    # 4. MatrixDilithiumNTT (全て NTT) を生成
    #    → あるいは MatrixDilithium(data_ntt) でもOK（NTT/Classic混在許容）
    matrix_ntt = MatrixDilithiumNTT(
        parent=parent, module=module, data=data_ntt
    )

    print(f"DEBUG: Created MatrixDilithiumNTT instance: {matrix_ntt}")
    print(f"DEBUG: MatrixDilithiumNTT data: {matrix_ntt._data}")

    # 5. Dilithium インスタンス
    dilithium = Dilithium(
        parameter_set, parent=parent, module=module, matrix=matrix_ntt
    )

    # 6. 鍵生成
    pq_public_key, pq_private_key = dilithium.keygen()
    message = b"Test message for Dilithium"

    # 7. 署名→検証テスト
    signature = dilithium.generate_signature(pq_private_key, message)
    assert dilithium.verify_signature(pq_public_key, message, signature)


def test_dilithium_invalid_signature():
    """
    同じように NTT ポリで行列を生成し、別の鍵で署名したものを検証して無効になるかをテスト。
    """
    parent = PolynomialRingDilithium(q=8380417, n=256, root_of_unity=1753)
    print(f"DEBUG: parent.ntt_zetas = {parent.ntt_zetas[:10]}")

    parameter_set = {
        "d": 14,
        "k": 4,
        "l": 4,
        "eta": 2,
        "tau": 39,
        "omega": 80,
        "gamma_1": 131072,  # 公式
        "gamma_2": 95232,    # 公式
        "beta": 196,          # 論文推奨値
    }

    module = ModuleDilithium(q=8380417)

    # NTT ポリ作成
    data_ntt = [
        [
            PolynomialDilithiumNTT(
                parent=parent,
                coeffs=[(i * 100 + j) % parent.q for j in range(parent.n)]
            )
            for j in range(4)
        ]
        for i in range(4)
    ]
    matrix_ntt = MatrixDilithiumNTT(
        parent=parent, module=module, data=data_ntt
    )

    # Dilithium インスタンス
    dilithium = Dilithium(
        parameter_set, parent=parent, module=module, matrix=matrix_ntt
    )
    another_dilithium = Dilithium(
        parameter_set, parent=parent, module=module, matrix=matrix_ntt
    )

    # 鍵生成
    pq_public_key, pq_private_key = dilithium.keygen()
    _, another_private_key = another_dilithium.keygen()

    # 偽の署名を生成
    invalid_signature = another_dilithium.generate_signature(
        another_private_key, b"Fake message"
    )

    # 署名検証 → False になるはず
    assert not dilithium.verify_signature(
        pq_public_key, b"Test message for Dilithium", invalid_signature
    )


def test_matrix_dilithium():
    """
    両対応: MatrixDilithium で NTT/Classic 両方許容テスト。
    ここでは NTT ポリを混在or単独で入れてテスト。
    """
    parent = PolynomialRingDilithium(q=8380417, n=256)
    module = ModuleDilithium(q=8380417)

    # ここではあえて PolynomialDilithiumNTT のみを格納
    A_data = [
        [
            PolynomialDilithiumNTT(
                parent=parent,
                coeffs=[(i * 100 + j) % parent.q for j in range(parent.n)]
            )
            for j in range(4)
        ]
        for i in range(4)
    ]

    matrix_dil = MatrixDilithium(parent=parent, module=module, data=A_data)
    assert matrix_dil.rows == 4
    assert matrix_dil.cols == 4

    print(f"Matrix: {matrix_dil}")
    # to_ntt() → 既にNTTの場合は同じかもしれないが、一応呼んでみる
    ntted = matrix_dil.to_ntt()
    print("NTT-ed matrix:", ntted)


def test_matrix_to_bytes():
    """
    modules_generic.Matrix の to_bytes() テスト
    """
    data = [[1, 2], [3, 4]]
    matrix = Matrix(parent=None, module=None, data=data)
    assert isinstance(matrix.to_bytes(), bytes)


def test_polynomial_to_bytes():
    """
    PolynomialDilithium の to_bytes() テスト
    """
    coefficients = [1, -2, 3]
    poly = PolynomialDilithium(coefficients=coefficients, parent=None)
    assert isinstance(poly.to_bytes(), bytes)


class DummyModule(ModuleDilithium):
    def __init__(self, q=8380417):
        super().__init__(q=q)


def main():
    """
    メイン関数:
      デフォルトの Dilithium2(パラメータ) を用いて鍵生成～署名～検証を行う。
    """
    print("鍵ペアを生成中...")
    pk, sk = Dilithium2.keygen()
    print(f"Public Key: {pk}")
    print(f"Secret Key: {sk}")

    # メッセージ署名
    msg = b"Test message for signature"
    print(f"署名するメッセージ: {msg}")
    sig = Dilithium2.sign(sk, msg)
    print(f"生成された署名: {sig}")

    # 検証
    is_valid = Dilithium2.verify(pk, msg, sig)
    print(f"署名の検証結果: {is_valid}")


if __name__ == "__main__":
    main()
