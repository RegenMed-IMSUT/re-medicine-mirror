# Re-medicine trial mirror / 再生医学分野・試験ミラー

## 日本語

東京大学医科学研究所 幹細胞治療研究センター 再生医学分野のサイトを、wgetで取得した時点の内容として保存した静的ミラーです。[原サイト](http://re-medicine.stemcell-imsut.org/)が正式版です。元サーバー・ドメイン・DNSは変更していません。Concrete CMSの管理画面、サーバー処理、自動同期は移行していません。

`docs/` が公開ルートです。GitHub PagesのプロジェクトURLのサブパスで使えるよう、ページ間と公開資産の相対参照を維持しています。47ページすべてに `noindex` と小さな「試験ミラー／原サイト」案内を追加しました。**noindexはアクセス制御ではありません。公開すれば誰でも閲覧できます。**

### 配置

- `docs/`: 47 HTMLページと資産、`.nojekyll`（計90ファイル。ブラウザー検証で判明した不足ヘッダー画像を含む）
- `tools/repair_runtime_header.py`: 原サイトからヘッダー画像を補完し、46ページのJavaScript内参照を相対化する追加処理。再生成した場合にも必要。実行前にROOTを再生成先へ合わせてください。
- `tests/test_runtime_assets.py`: 動的ヘッダー画像の回帰テスト。
- `tools/prepare_mirror.py`: Python標準ライブラリだけで動く変換・静的検査
- `tests/test_prepare_mirror.py`: 小さな実ファイルを使う検査テスト
- `_upload_metadata/`: 原本／変換後SHA-256、88ファイルの対応TSV、検査JSON。`docs/`の外に置き、サイト配信対象にはしません。

GitHub Pagesの設定は `main` ブランチの `/docs` です。独自ドメイン用のCNAMEや独自Actionsは追加していません。試験公開先: https://regenmed-imsut.github.io/re-medicine-mirror/ 。

### ローカル検査・変換

Python 3.10以降が必要です。依存パッケージのインストールは不要です。リポジトリ直下から:

```bash
python -B -m unittest discover -s tests -v
python -B tools/prepare_mirror.py --check docs
```

原本から再生成する場合は、**新しい空の出力先**を明示してください。既存の `docs/` は上書きせず停止します。原本と出力先の重複、名前衝突、未知の拡張子なしファイルも停止条件です。

```bash
python -B tools/prepare_mirror.py --source 'C:/Users/walkv/Desktop/website/gnu/re-medicine/re-medicine.stemcell-imsut.org' --output 'C:/Users/walkv/Desktop/website/github-pages/re-medicine-mirror-fresh'
```

### 変更と既存の問題

- wgetのU+F03F付き資産17件を通常のJS/CSS名へ変更し、参照も更新しました。
- `download_file/17/0` はJPEG、18/19はPNGのマジックバイトを確認し、`.jpg`／`.png` を追加しました。画像データそのものは変更していません。
- 旧サーバーのTileImage（144pxファイル）は原本に含まれていませんでした。全ページで既存のローカル `RegeneMedLogoSquire.png` を相対参照するようにしました。別解像度の画像を新規取得・生成してはいません。
- YouTube iframe 2件をHTTPS化しました。Bootstrap、Font Awesome、Google Fonts、YouTube、Google Maps等の外部依存は維持しています。
- Concreteの `CCM_*` は、保存済みHTML/JSで定義以外の使用が見つからなかったため残しています。旧ドメイン文字列やルート絶対文字列が宣言に残っていても、検査済みの静的表示資産参照とは別です。
- `news/2023.html` の `http://https://www.ims.u-tokyo.ac.jp/imsut/jp/events/others/network2023_00001.html` は既存の不正外部リンクです。承認対象外の修正を避け、そのまま記録しています。

静的検査ではHTML属性、srcset、インラインCSS、CSSのurl/importに対するローカル欠落、ルート絶対参照、HTTP能動参照、不安全名を検査します。ブラウザーの表示・メニュー・フォーム用テンプレートJSの非発火、動的URL、アンカー、HTTPのContent-Type、外部サイトの到達性は別途確認が必要です。静的検査合格だけで公開後の動作確認済みとはしません。

### 権利

掲載写真、人物情報、ロゴ、文章、論文等の権利は各権利者に帰属します。本リポジトリ全体やサイト内容にMIT等の一括ライセンスは付与していません。既存のライブラリ内のライセンス表記は維持しています。試験公開の承認は、第三者への自由な再利用許諾を意味しません。

## English

This is a static trial mirror of the Division of Regenerative Medicine website, captured with wget. The [original website](http://re-medicine.stemcell-imsut.org/) remains authoritative. The original files, server, domain and DNS have not been changed. Concrete CMS administration, server-side processing and automatic synchronization are not included.

Serve only `docs/`. Relative paths support a GitHub Pages project subpath. Every HTML page includes `noindex` and a short trial-mirror notice linking to the original. **noindex does not restrict access: a published mirror is publicly readable.** GitHub Pages serves the `main` branch `/docs` at https://regenmed-imsut.github.io/re-medicine-mirror/ . Runtime browser checks identified a missing header image; it was fetched from the original public HTTP endpoint and 46 inline JavaScript paths were made relative. Seven tests pass; representative desktop pages and the mobile menu were checked. External video/map playback remains dependent on third-party services.

The standard-library Python tool removes wget query suffixes from filenames, detects collisions, adds image extensions based on magic bytes, updates references, and records SHA-256 manifests and validation results outside `docs/`. Existing output is never overwritten; regenerate into a fresh directory. Run the two local check commands above before changes or deployment.

External CDNs, fonts, YouTube and Maps remain dependencies. The malformed external link in `news/2023.html` is preserved and recorded. Unused Concrete declarations are retained. Browser behavior, dynamic requests, anchors, HTTP responses and external availability still need separate verification.

No blanket license is granted for the site, photographs, personal information, logos, publications or other third-party content. Existing bundled library notices are retained. Permission to publish a trial mirror is not permission for unrestricted reuse.
