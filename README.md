# Tổng quan các bài tập AI

README này tóm tắt các module, dữ liệu và luồng chạy hiện có trong `ex1`, `ex2`, `ex3`. `ex1` giải N-Queens, `ex2` xây dựng Tank Battle với agent có thể thay thế, còn `ex3` mô hình hóa và giải Kakuro bằng CSP.

## Cấu trúc

```text
source/
├── ex1/
│   ├── nqueens_cnf.py
│   ├── nqueens_sat.py
│   ├── nqueens_minconflicts.py
│   └── results_minconflicts.csv
├── ex2/
│   ├── arena.py
│   ├── agent_loader.py
│   ├── agents/                 # agent plugin mẫu và hướng dẫn API
│   ├── tank_game.py
│   ├── tank_ai.py
│   ├── tank_experiements.py
│   ├── tank_gui.py             # hiện chưa có nội dung
│   └── results_*.csv
└── ex3/
    ├── kakuro_csp.py
    ├── kakuro_solver.py
    ├── kakuro_trace.py
    ├── kakuro_gui.py
    ├── kakuro_experiments.py
    ├── generate_puzzle.py
    ├── puzzles/                # puzzle mẫu dạng .txt
    └── results_*.csv
```

## Sơ đồ pipeline

![Sơ đồ pipeline luồng chạy của ex1, ex2 và ex3](exercise-pipelines.svg)

Mũi tên chỉ luồng dữ liệu chính; hai nhánh trong `ex1` là các thuật toán giải độc lập.

## Đối chiếu yêu cầu của đề bài với dự án

Mục này liệt kê từng yêu cầu trong đề (Final Project, môn Introduction to AI 503043) và chỉ ra phần tương ứng trong dự án: file, hàm hoặc lớp thực hiện, kết quả sinh ra, và phần nào phải viết trong báo cáo (Task 4). Ký hiệu **YC** là "yêu cầu" (Requirement) của đề. Điểm tối đa theo đề: Task 1 gồm 1.0 + 1.0 + 1.0, Task 2 gồm 1.0 + 1.5 + 0.5, Task 3 gồm 1.0 + 1.0 + 1.0.

### Bảng tổng hợp

| Yêu cầu | Điểm | Nội dung đề yêu cầu | File / hàm chính | Trạng thái |
|---|---|---|---|---|
| ex1 – YC1 | 1.0 | Mô hình logic mệnh đề, thuật toán khám phá ràng buộc, chuyển sang CNF | `ex1/nqueens_cnf.py` | Có code. Phần thảo luận viết trong báo cáo |
| ex1 – YC2 | 1.0 | Giải bằng Glucose3, thí nghiệm N tăng dần (N ≥ 4), báo số mệnh đề và thời gian | `ex1/nqueens_sat.py` | Có code. Cần chạy trên máy đánh giá để có `results_sat.csv` (chưa có trong cấu trúc liệt kê ở trên) |
| ex1 – YC3 | 1.0 | Min-Conflicts, đề xuất heuristic chọn biến, so sánh với bản chuẩn | `ex1/nqueens_minconflicts.py`, `results_minconflicts.csv` | Có code và kết quả |
| ex2 – YC1 | 1.0 | Mô hình Zero-Sum Game: trạng thái, người chơi, hành động, chuyển trạng thái, terminal, utility; cách áp dụng tìm kiếm đối kháng | `ex2/tank_game.py` | Có code. Phần thảo luận viết trong báo cáo |
| ex2 – YC2 | 1.5 | Thuật toán điều khiển xe tăng, tối ưu thời gian thực, thí nghiệm 4 cấu hình | `ex2/tank_ai.py`, `ex2/tank_experiements.py`, `results_*.csv` | Có code và kết quả |
| ex2 – YC3 | 0.5 | Giao diện PyGame, cơ chế nạp thuật toán của nhóm khác, cho các thuật toán đấu nhau | `ex2/tank_gui.py`, `ex2/agent_loader.py`, `ex2/arena.py`, `ex2/agents/` | Cơ chế nạp và đấu đã có. **`tank_gui.py` đang trống nên phần giao diện chưa đạt**, xem ghi chú ở YC3 |
| ex3 – YC1 | 1.0 | Mô hình CSP: biến, miền, ràng buộc; mô tả và biện minh thuật toán | `ex3/kakuro_csp.py` (mô hình), `ex3/kakuro_solver.py` (kỹ thuật) | Có code. Phần mô tả và biện minh viết trong báo cáo |
| ex3 – YC2 | 1.0 | Solver giải được bài; chứng minh tính đúng, ổn định, hiệu quả trên bảng phức tạp | `ex3/kakuro_solver.py`, `ex3/kakuro_experiments.py`, `puzzles/complex_9x9.txt` | Có code và kết quả |
| ex3 – YC3 | 1.0 | Giao diện thể hiện miền biến, quá trình lan truyền ràng buộc, quá trình Backtracking | `ex3/kakuro_trace.py`, `ex3/kakuro_gui.py` | Có code. Cần chạy với PyGame thật để chụp hình cho báo cáo |

### ex1 – N-Queens (Local Search và Propositional Logic)

**Mô tả đề:** bàn cờ N × N, đặt N quân hậu không có cặp nào tấn công nhau; mỗi ô là một biến logic, True nghĩa là ô có hậu, False nghĩa là ô trống.
Ánh xạ trong dự án: `Board.var(r, c)` đổi ô (r, c) thành biến mệnh đề `r·N + c + 1`; `Board.num_vars` bằng N².

#### ex1 – YC1 (1.0 điểm): mô hình hóa bằng logic mệnh đề

**Đề yêu cầu:**
1. Mô hình bài toán thành bài toán logic mệnh đề và giới thiệu các thành phần liên quan.
2. Thảo luận thuật toán khám phá các ràng buộc chi phối việc đặt hậu.
3. Giải thích quy trình chuyển các ràng buộc sang mệnh đề CNF.

**Trong dự án:**
- Thành phần của mô hình (biến, ánh xạ ô thành biến): `Board` (`var`, `square`, `squares`, `num_vars`).
- Khám phá ràng buộc: `ConstraintGenerator.attacks` (hai ô tấn công nhau khi cùng hàng, cùng cột hoặc cùng đường chéo), `attacking_pairs_naive` (duyệt mọi cặp ô) và `attacking_pairs_grouped` (gom ô theo hàng, cột, đường chéo rồi ghép cặp trong từng nhóm).
- Chuyển sang CNF: `at_least_one_per_row` (mệnh đề "mỗi hàng có ít nhất một hậu") và `at_most_one_clauses` (mỗi cặp ô tấn công nhau cho mệnh đề `¬x(a) ∨ ¬x(b)`), gộp bởi `generate`; công thức đã ở dạng CNF nên lưu trong `CNFFormula` và xuất được bằng `to_dimacs`.
- Kiểm chứng: `expected_clause_count` cho công thức số mệnh đề `N + 2N·C(N,2) + 4·C(N,3) + 2·C(N,2)` để đối chiếu với số mệnh đề thật.
- **Trong báo cáo:** phần "thảo luận" và "giải thích quy trình" cần viết thành văn bản (công thức, ví dụ bàn cờ 4×4, khử kéo theo `x(a) → ¬x(b) ≡ ¬x(a) ∨ ¬x(b)`).

#### ex1 – YC2 (1.0 điểm): Glucose3 và thí nghiệm khi N tăng

**Đề yêu cầu:**
1. Dùng solver Glucose3 của thư viện PySAT để tìm lời giải.
2. Thí nghiệm với N tăng dần, N ≥ 4.
3. Với mỗi N, báo cáo tổng số mệnh đề CNF và thời gian chạy của solver.

**Trong dự án:**
- `SATQueensSolver` (`build`, `solve`): tạo CNF, gọi Glucose3, đo riêng thời gian sinh CNF và thời gian giải (đề chỉ yêu cầu thời gian của solver, nên cột `solve_time_s` là số liệu cần báo cáo).
- `SATQueensSolver.is_valid`: kiểm tra độc lập lời giải.
- `ExperimentRunner` (`run`, `save_csv`, `plot`): chạy nhiều giá trị N, ghi số biến, số mệnh đề, thời gian, tính hợp lệ.
- Đầu ra: `results_sat.csv` và `results_sat.png` (sinh ra khi chạy `nqueens_sat.py`).
- **Lưu ý:** số liệu thời gian phải đo trên máy theo cấu hình đánh giá của đề (macOS 13.7.8, Intel Core i5). Cần chạy lại và lưu `results_sat.csv` vào thư mục `ex1`.

#### ex1 – YC3 (1.0 điểm): Min-Conflicts và heuristic chọn biến

**Đề yêu cầu:**
1. Giải bằng thuật toán Min-Conflicts (Lecture 08).
2. Đề xuất một heuristic chọn biến.
3. Thí nghiệm đánh giá hiệu quả của heuristic bằng cách so sánh với Min-Conflicts chuẩn.

**Trong dự án:**
- Min-Conflicts: `MinConflictsSolver` (`random_initial`, `best_value`, `solve`) cùng `QueensState` (bộ đếm hàng và đường chéo để tính xung đột nhanh).
- Bản chuẩn (baseline): `RandomSelector`, chọn ngẫu nhiên một cột đang xung đột.
- Heuristic đề xuất: `MaxConflictSelector` (cột nhiều xung đột nhất) và `MaxConflictTabuSelector` (thêm tabu để tránh lặp vòng).
- Thí nghiệm so sánh: `Experiment` (`run`, `save_csv`), tính tỷ lệ thành công, số bước trung bình, thời gian trung bình với cùng trạng thái đầu cho cả ba bộ chọn.
- Kết quả: `results_minconflicts.csv` (N = 8, 16, 32, 64, 128, 256).
- **Trong báo cáo:** nêu rõ heuristic đề xuất, bảng so sánh và nhận xét (heuristic giảm số bước nhưng thời gian gần như không đổi vì mỗi bước tốn thêm O(N) để chọn cột lớn nhất).

**Lưu ý chung của Task 1 (phần Notice trong đề):** code phải theo nguyên tắc OOP (đã dùng các lớp `Board`, `CNFFormula`, `ConstraintGenerator`, `SATQueensSolver`, `QueensState`, `VariableSelector`, `MinConflictsSolver`); số liệu đánh giá trên macOS 13.7.8, Intel Core i5.

### ex2 – Tank Battle (Adversarial Search)

**Mô tả đề:** game theo lượt, xe tăng đi một ô mỗi lượt (UP, DOWN, LEFT, RIGHT), đạn bay 3 ô mỗi chu kỳ và kiểm tra va chạm sau từng ô, đạn dừng ngay khi trúng; HP và sát thương: Tank 6 HP, Base 9 HP, Wall 3 HP, mỗi lần trúng 1 sát thương; 6 hành động `MOVE_UP, MOVE_DOWN, MOVE_LEFT, MOVE_RIGHT, FIRE, STAY`; game kết thúc khi căn cứ hoặc xe tăng bị phá.
Ánh xạ trong dự án: hằng số `TANK_HP`, `BASE_HP`, `WALL_HP`, `BULLET_SPEED` và `MAX_CYCLES` trong `tank_game.py`; enum `Action` (6 hành động); `GameState._move_bullets` (đạn bay từng ô, va chạm, sát thương); `GameState.is_terminal` (kết thúc).

#### ex2 – YC1 (1.0 điểm): mô hình Zero-Sum Game

**Đề yêu cầu:**
1. Mô hình bài toán thành trò chơi tổng bằng không.
2. Giới thiệu các thành phần: trạng thái game, người chơi, hành động, hàm chuyển trạng thái, trạng thái kết thúc, hàm lợi ích (utility).
3. Thảo luận cách áp dụng Minimax Search, Alpha-Beta Pruning và Heuristic Minimax Search để điều khiển xe tăng.

**Trong dự án (`ex2/tank_game.py`):**

| Thành phần theo đề | Nằm ở đâu |
|---|---|
| Trạng thái game | `GameState` (tường và HP, xe tăng `Tank`, căn cứ `Base`, đạn `Bullet`, lượt chơi, số chu kỳ); `GameConfig` (bản đồ); `GameState.key` (dạng băm) |
| Người chơi | `MAX_PLAYER` (xe tăng của ta) và `MIN_PLAYER` (đối thủ); `utility` tính từ góc nhìn MAX nên U_MIN = −U_MAX |
| Hành động | `Action`; `GameState.legal_actions` (luôn có `STAY`, chỉ cho `FIRE` khi chưa có đạn bay) |
| Hàm chuyển trạng thái | `GameState.apply` (áp dụng hành động lên bản sao, sau lượt MIN thì gọi `_move_bullets` và tăng chu kỳ) |
| Trạng thái kết thúc | `GameState.is_terminal` (cùng `_destroyed`; hoặc hết giới hạn chu kỳ thì hòa) |
| Hàm lợi ích | `GameState.utility` (thắng sớm có điểm cao hơn, hòa bằng 0) |

- Áp dụng thuật toán tìm kiếm lên mô hình này nằm ở `tank_ai.py` (xem YC2).
- **Trong báo cáo:** phần thảo luận cách áp dụng Minimax, Alpha-Beta và Heuristic Minimax; nêu các giả định (MAX đi trước rồi MIN, mỗi xe tối đa một đạn đang bay, đi vào ô bị chặn thì chỉ quay hướng).

#### ex2 – YC2 (1.5 điểm): thuật toán điều khiển và thí nghiệm bốn cấu hình

**Đề yêu cầu:**
1. Cài đặt thuật toán điều khiển xe tăng; có thể dùng các kỹ thuật tối ưu để xe tăng hoạt động hiệu quả và game chạy theo thời gian thực.
2. Thiết lập thí nghiệm so sánh thời gian tính toán và hiệu năng tìm kiếm của bốn cấu hình: Minimax Search, Alpha-Beta Search, Heuristic Minimax Search, Heuristic Minimax kèm Alpha-Beta Pruning.
3. Dùng cùng kịch bản game và điều kiện tìm kiếm để so sánh công bằng.
4. Các độ đo gợi ý: thời gian thực thi, số trạng thái được khám phá, độ sâu tìm kiếm và các độ đo phù hợp khác.

**Trong dự án:**
- Bốn cấu hình: `SearchAgent.CONFIGS` trong `tank_ai.py`, chạy trên cùng lớp `Searcher` (bật hoặc tắt `use_alpha_beta` và `use_heuristic`).
- Hàm đánh giá của Heuristic Minimax: `HeuristicEvaluator` (`evaluate`, `_aim`, `first_hit`).
- Kỹ thuật tối ưu: `Searcher.ordered_actions` (sắp xếp nước đi, cùng thứ tự cho cả bốn cấu hình), iterative deepening với giới hạn thời gian trong `Searcher.search`, và `legal_actions` bỏ các nước vô tác dụng.
- Cùng kịch bản và điều kiện: `make_scenarios` (trạng thái đầu và các trạng thái giữa trận cố định bằng seed) trong `tank_experiements.py`.
- Các độ đo: số node, số lá, số lần cắt tỉa, độ sâu hoàn tất, thời gian (lưu trong thống kê của `Searcher`).
- Ba thí nghiệm:
  - `experiment_cost`: số node, thời gian, số lần cắt tỉa theo độ sâu; đồng thời kiểm tra Alpha-Beta cho cùng giá trị và hành động với Minimax. Đầu ra `results_cost.csv`.
  - `experiment_depth_budget`: độ sâu đạt được trong một ngân sách thời gian cố định. Đầu ra `results_depth_budget.csv`.
  - `experiment_matches` (cùng `play_match` và `openings`): các cấu hình đấu vòng tròn từ nhiều khai cuộc. Đầu ra `results_matches.csv`.
- **Lưu ý:** tên file hiện là `tank_experiements.py`; số liệu cần chạy lại trên máy đánh giá (Intel Core i5).

#### ex2 – YC3 (0.5 điểm): giao diện PyGame và nạp thuật toán nhóm khác

**Đề yêu cầu:**
1. Cài đặt giao diện đồ họa bằng thư viện PyGame để vận hành trò chơi.
2. Có cơ chế nhập và tích hợp thuật toán của các nhóm sinh viên khác.
3. Cho phép các cách cài đặt thuật toán khác nhau thi đấu với nhau trong cùng môi trường game.

**Trong dự án:**
- Cơ chế nạp thuật toán nhóm khác: `agent_loader.py` (`load_agent_from_file`, `discover_agent_files`, `builtin_specs`, `file_spec`, `all_specs`) và hợp đồng giao tiếp trong `agents/README.md` (bốn kiểu plugin: `AGENT`, `create_agent()`, class có `choose_action`, hàm `choose_action(state)`). Ví dụ plugin: `agents/greedy_agent.py`, `agents/function_agent.py`.
- Cho các thuật toán thi đấu trong cùng môi trường: `arena.py` (`GameController` chạy agent trong luồng riêng, quá giờ, lỗi hoặc sai kiểu đều thành `STAY`; `run_match`, `random_openings`, `head_to_head`). Chạy đấu không giao diện bằng `python arena.py <agent_a> <agent_b> --games 3`.
- Giao diện PyGame: `tank_gui.py` (menu chọn người chơi cho từng bên gồm người, Random, bốn cấu hình, plugin; nạp plugin bằng phím L hoặc kéo thả file; hiển thị bản đồ, HP, đạn, thời gian suy nghĩ).
- **Lưu ý quan trọng:** trong cấu trúc hiện tại của repo, `ex2/tank_gui.py` đang rỗng. Do đó phần "giao diện PyGame" của YC3 chưa có code trong repo; cần đặt nội dung `tank_gui.py` vào `source/ex2/` rồi kiểm tra với PyGame thật. Cơ chế nạp và đấu thì đã có sẵn ở `agent_loader.py` và `arena.py`.

**Lưu ý chung của Task 2 (Notice):** theo nguyên tắc OOP; số liệu đánh giá trên macOS 13.7.8, Intel Core i5.

### ex3 – Kakuro (Constraint Satisfaction Problems)

**Mô tả đề:** hiểu luật Kakuro; mô hình bài toán thành CSP bằng cách xác định biến, miền giá trị và ràng buộc; xây dựng solver kết hợp kỹ thuật lan truyền ràng buộc (constraint propagation) với Backtracking Search; dùng các heuristic đã học ở Lecture 08 để tăng hiệu quả tìm kiếm.

#### ex3 – YC1 (1.0 điểm): mô hình CSP

**Đề yêu cầu:**
1. Mô hình hóa đúng bài toán thành CSP, xác định và giải thích các thành phần: biến, miền giá trị, ràng buộc.
2. Mô tả và biện minh các thuật toán và kỹ thuật dùng trong dự án.

**Trong dự án:**

| Thành phần theo đề | Nằm ở đâu |
|---|---|
| Biến | Mỗi ô trắng là một biến: `KakuroCSP.variables` (từ `KakuroPuzzle.white`) |
| Miền giá trị | Chữ số 1 đến 9, thu hẹp ban đầu bằng các tổ hợp hợp lệ của từng dãy: `KakuroCSP.domains`, `Run.combos`, `Run.allowed_digits` |
| Ràng buộc | Mỗi dãy (`Run`, trích bởi `KakuroPuzzle._extract_runs`) vừa phải đôi một khác nhau vừa có tổng đúng gợi ý; `Run.consistent` kiểm tra cục bộ; quan hệ láng giềng `KakuroCSP.neighbors`, `runs_of` |
| Kiểm tra nghiệm và thống kê mô hình | `KakuroCSP.is_solution`, `KakuroCSP.statistics`, `KakuroCSP.consistent` |
| Đọc bảng | `KakuroPuzzle.from_text` (định dạng `.` ô trắng, `#` ô đen, `down\across` gợi ý) |

- Các kỹ thuật cần mô tả và biện minh nằm ở `kakuro_solver.py`: thu hẹp miền bằng tổ hợp, lan truyền all-different và lọc tổ hợp (`KakuroSolver._propagate`, `_revise`), Backtracking với MRV, Degree, LCV (`_select`, `_order_values`), restart ngẫu nhiên (`solve_with_restarts`).
- **Trong báo cáo:** phần giải thích mô hình và phần biện minh lý do chọn từng kỹ thuật (dựa trên số liệu ở YC2).

#### ex3 – YC2 (1.0 điểm): solver và đánh giá trên bảng phức tạp

**Đề yêu cầu:**
1. Cài đặt solver tìm được nghiệm hợp lệ cho bài toán.
2. Chứng minh và đánh giá tính đúng đắn (correctness), tính ổn định (stability) và hiệu quả (effectiveness) bằng cách áp dụng lên bảng test phức tạp hơn do đề cung cấp.

**Trong dự án:**
- Solver kết hợp lan truyền ràng buộc và Backtracking: `KakuroSolver` (`solve`, `count_solutions`, `solve_with_restarts`, `SolverStats`); các kỹ thuật bật tắt được (`propagation`, `mrv`, `degree`, `lcv`).
- Bảng phức tạp của đề: `puzzles/complex_9x9.txt` (bảng 9×9 chép lại từ ảnh trong đề).
- Ba tiêu chí đề yêu cầu, trong `kakuro_experiments.py`:

| Tiêu chí | Thí nghiệm | Nội dung | Đầu ra |
|---|---|---|---|
| Tính đúng đắn | A: `experiment_correctness`, `verify_independent` | Kiểm tra nghiệm trực tiếp từ văn bản bảng, đếm nghiệm (duy nhất hay không), so sánh nghiệm giữa các cấu hình | in ra màn hình |
| Hiệu quả | B: `experiment_ablation` | So sánh từng kỹ thuật (số node, backtrack, lần lan truyền, thời gian) | `results_ablation.csv` |
| Tính ổn định | C: `experiment_stability` | Chạy nhiều lần với seed khác nhau (ngẫu nhiên hóa thứ tự hòa và thứ tự giá trị) | `results_stability.csv` |
| Mở rộng (bổ sung) | D: `experiment_scaling` | Bảng sinh ngẫu nhiên kích thước tăng dần, có và không có restart | `results_scaling.csv` |

- Dữ liệu hỗ trợ: `generate_puzzle.py` (`generate`, `random_pattern`) sinh bảng có nghiệm biết trước; `puzzles/demo_6x5.txt`, `puzzles/demo_backtracking.txt`.
- **Trong báo cáo:** bảng và nhận xét từ ba thí nghiệm A, B, C. Nên nói rõ giới hạn đã thấy ở D (bảng sinh ngẫu nhiên khó hơn bảng thiết kế).

#### ex3 – YC3 (1.0 điểm): giao diện trực quan hóa

**Đề yêu cầu:** cài đặt giao diện (UI) cho trò chơi thể hiện rõ ba nội dung: miền giá trị của các biến, quá trình lan truyền ràng buộc, và quá trình Backtracking Search.

**Trong dự án:**

| Nội dung đề yêu cầu | Nằm ở đâu |
|---|---|
| Miền giá trị của biến | `TraceStep.domains` (ảnh chụp miền ở mỗi bước, do `kakuro_trace.py: TraceRecorder` ghi); `kakuro_gui.py` vẽ các chữ số ứng viên trong lưới 3×3 nhỏ của mỗi ô, hoặc một chữ số lớn khi miền chỉ còn một giá trị |
| Quá trình lan truyền ràng buộc | Các bước `revise` và `conflict` (sự kiện từ `KakuroSolver._propagate`); giao diện viền vàng dãy đang xử lý, viền cam các ô vừa bị thu hẹp miền, tô đỏ khi xung đột |
| Quá trình Backtracking Search | Các bước `assign` và `backtrack` (chữ số xanh dương là quyết định tìm kiếm), độ sâu, bộ đếm số lần gán, quay lui, xung đột trong bảng thông tin |
| Điều khiển xem quá trình | `KakuroApp.handle`, `update`, `draw`: phát tự động, đi từng bước tới hoặc lui, đổi tốc độ, nhảy tới xung đột hoặc quay lui kế tiếp, đổi ba cấu hình (`PRESETS` trong `kakuro_trace.py`), nạp bảng khác |

- Bảng nên dùng khi trình diễn: `puzzles/complex_9x9.txt` (thấy rõ lan truyền) và `puzzles/demo_backtracking.txt` (có xung đột và quay lui).
- **Lưu ý:** cần chạy `kakuro_gui.py` với PyGame thật để chụp ảnh và quay video cho báo cáo và `demo.txt`.

**Lưu ý chung của Task 3 (Notice):** theo nguyên tắc OOP; số liệu đánh giá trên macOS 13.7.8, Intel Core i5.

### Lưu ý khi nộp (liên quan đến ex1–ex3)

- Đề yêu cầu trong thư mục `source` mỗi task nằm trong một thư mục con, có `README.md` và `requirement.txt` để cài đặt môi trường. Cấu trúc ở đầu tài liệu chưa liệt kê `requirement.txt`. Gợi ý nội dung: ex1 cần `python-sat` (và `matplotlib` nếu vẽ biểu đồ), ex2 và ex3 cần `pygame`.
- Đề cũng nêu rằng với file `ipynb` phải giữ nguyên output của mọi ô; nếu có dùng notebook thì cần chạy và lưu output trước khi nộp.
- Các phần "thảo luận" và "giải thích" của YC1 ở cả ba task, cùng phần tự đánh giá và đóng góp, thuộc Task 4 (báo cáo IEEE, tối đa 5 trang) và phải giải thích được khi phỏng vấn.

## `ex1`: N-Queens

Bài toán đặt `N` quân hậu lên bàn cờ `N x N` sao cho không quân nào ăn được quân nào. Có hai hướng giải trong thư mục: chuyển ràng buộc thành công thức logic CNF rồi dùng SAT solver, hoặc dùng tìm kiếm cục bộ Min-Conflicts.

### [source/ex1/nqueens_cnf.py](source/ex1/nqueens_cnf.py)

> **Thuộc yêu cầu:** ex1 – YC1 (mô hình logic mệnh đề, khám phá ràng buộc, chuyển CNF). Cũng là nền cho ex1 – YC2.

Xây dựng mô hình logic CNF cho N-Queens.

- `Board` ánh xạ mỗi ô `(hàng, cột)` thành ID biến mệnh đề và chuyển ngược lại; đồng thời đổi mô hình SAT thành các vị trí quân hậu và in bàn cờ.
- `CNFFormula` lưu các mệnh đề và có thể xuất công thức theo định dạng DIMACS.
- `ConstraintGenerator` sinh ràng buộc: mỗi hàng có ít nhất một hậu và không có hai hậu cùng hàng, cột hoặc đường chéo. Có cách sinh cặp quân tấn công trực tiếp (naive) và cách gom ô theo hàng/cột/đường chéo (grouped) để giảm công việc.
- Khi chạy trực tiếp, chương trình so sánh số mệnh đề của hai cách sinh trên một số kích thước bàn cờ.

Đây là module nền, được `nqueens_sat.py` dùng để tạo công thức và kiểm tra lời giải.

### [source/ex1/nqueens_sat.py](source/ex1/nqueens_sat.py)

> **Thuộc yêu cầu:** ex1 – YC2 (Glucose3, thí nghiệm khi N tăng, báo số mệnh đề và thời gian).

Giải N-Queens bằng SAT solver Glucose3 từ thư viện PySAT.

- `SATQueensSolver` tạo CNF, gọi Glucose3, đo riêng thời gian sinh CNF và thời gian giải, rồi chuyển mô hình trả về thành vị trí các quân hậu.
- `is_valid` kiểm tra độc lập rằng lời giải có đủ `N` quân và không có cặp nào tấn công nhau.
- `ExperimentRunner` chạy thử nhiều kích thước bàn cờ, in thống kê, lưu CSV và có thể vẽ đồ thị nếu đã cài `matplotlib`.
- Khi chạy trực tiếp, chương trình in một lời giải cho bàn cờ 8x8, sau đó chạy thí nghiệm và ghi `results_sat.csv` cùng biểu đồ `results_sat.png` vào thư mục làm việc hiện tại.

Phụ thuộc chính: `python-sat`; `matplotlib` chỉ cần cho phần vẽ biểu đồ.

### [source/ex1/nqueens_minconflicts.py](source/ex1/nqueens_minconflicts.py)

> **Thuộc yêu cầu:** ex1 – YC3 (Min-Conflicts, heuristic chọn biến, so sánh với bản chuẩn).

Giải N-Queens bằng thuật toán tìm kiếm cục bộ Min-Conflicts, không cần SAT solver.

- Trạng thái lưu một hậu cho mỗi cột; `rows[c]` là hàng của hậu ở cột `c`. Nhờ vậy ràng buộc mỗi cột có đúng một hậu luôn được thỏa mãn.
- `QueensState` duy trì số hậu trên từng hàng và hai hướng đường chéo để tính xung đột nhanh, cập nhật khi di chuyển hậu.
- Các bộ chọn biến gồm chọn ngẫu nhiên một cột đang xung đột, chọn cột có nhiều xung đột nhất, và biến thể chọn xung đột lớn nhất kèm tabu để hạn chế lặp vòng.
- `MinConflictsSolver` tạo trạng thái ban đầu ngẫu nhiên, chọn một cột xung đột rồi chuyển hậu trong cột đó đến hàng ít xung đột nhất; dừng khi tìm được lời giải hoặc đạt giới hạn bước.
- `Experiment` chạy nhiều lần cho từng kích thước và bộ chọn, rồi tổng hợp tỷ lệ thành công, số bước trung bình và thời gian trung bình.
- Khi chạy trực tiếp, chương trình in thử cho `N=8` và chạy thí nghiệm cho các kích thước từ 8 đến 256.

### [results_minconflicts.csv](source/ex1/results_minconflicts.csv)

> **Thuộc yêu cầu:** ex1 – YC3 (kết quả so sánh heuristic với Min-Conflicts chuẩn).

Kết quả thí nghiệm Min-Conflicts đã được lưu sẵn. Mỗi dòng là một cặp kích thước `N` và thuật toán chọn biến, với các cột:

- `success_rate`: tỷ lệ lần chạy tìm được lời giải.
- `avg_steps`: số bước trung bình.
- `avg_time_s`: thời gian chạy trung bình tính bằng giây.

Dữ liệu hiện có cho `N = 8, 16, 32, 64, 128, 256`, mỗi kích thước so sánh ba bộ chọn. Đây là kết quả đã lưu, không phải file được tự động đọc bởi solver.

## `ex2`: Tank Battle

Bài tập mô hình hóa Tank Battle thành game hai người chơi đối kháng, tổng bằng không, sau đó dùng tìm kiếm cây trò chơi để chọn hành động.

### [tank_game.py](source/ex2/tank_game.py)

> **Thuộc yêu cầu:** ex2 – YC1 (trạng thái, người chơi, hành động, chuyển trạng thái, terminal, utility).

Chứa luật chơi và trạng thái game; đây là nền tảng mà agent tìm kiếm dùng.

- Các kiểu `Tank`, `Base`, `Bullet`, `Direction` và `Action` biểu diễn đơn vị, hướng và hành động.
- `GameConfig` định nghĩa kích thước bàn cờ, vị trí ban đầu và tường mặc định đối xứng.
- `GameState` quản lý tường và HP, xe tăng, căn cứ, đạn, lượt chơi và số chu kỳ. Nó cung cấp trạng thái ban đầu, sao chép, kiểm tra nước đi hợp lệ, áp dụng hành động để tạo trạng thái mới, di chuyển đạn/xử lý va chạm, nhận diện kết thúc, tính utility và in bàn cờ dạng ASCII.
- Người chơi MAX là xe tăng của ta, MIN là đối thủ. MAX đi trước; sau lượt MIN thì đạn di chuyển và chu kỳ tăng lên.
- Chạy trực tiếp file sẽ in bàn cờ ban đầu cùng các hành động hợp lệ của MAX.

### [tank_ai.py](source/ex2/tank_ai.py)

> **Thuộc yêu cầu:** ex2 – YC2 (thuật toán điều khiển xe tăng, bốn cấu hình tìm kiếm, kỹ thuật tối ưu).

Triển khai các agent chọn hành động dựa trên tìm kiếm đối kháng.

- `HeuristicEvaluator` chấm điểm trạng thái không kết thúc dựa trên HP xe tăng/căn cứ, khả năng ngắm bắn, đạn đang bay và khoảng cách tới căn cứ đối thủ.
- `Searcher` thực hiện Minimax, có thể bật cắt tỉa Alpha-Beta và heuristic. Tìm kiếm có thể chạy đến độ sâu cố định hoặc iterative deepening trong giới hạn thời gian; thống kê gồm số node, lá, lần cắt tỉa, độ sâu hoàn tất và thời gian.
- Bốn cấu hình được so sánh: Minimax, Alpha-Beta, Minimax có heuristic, và Minimax có heuristic kèm Alpha-Beta.
- `RandomAgent` chọn ngẫu nhiên một nước hợp lệ; `SearchAgent` dùng cấu hình tìm kiếm đã chọn để ra quyết định.
- Giá trị tìm kiếm được quy đổi theo góc nhìn của người đang đi, nên cùng một loại agent có thể điều khiển cả MAX lẫn MIN.

Module này import luật chơi từ `tank_game.py`.

### [tank_experiements.py](source/ex2/tank_experiements.py)

> **Thuộc yêu cầu:** ex2 – YC2 (thí nghiệm so sánh bốn cấu hình trên cùng kịch bản).

Tạo tình huống chơi và đánh giá bốn cấu hình tìm kiếm trong ba loại thí nghiệm.

- `make_scenarios` tạo trạng thái ban đầu và các trạng thái giữa trận có thể tái lập bằng seed.
- Thí nghiệm A so sánh số node, thời gian, số lần cắt tỉa ở các độ sâu; đồng thời kiểm tra Alpha-Beta trả cùng giá trị và hành động với Minimax tương ứng.
- Thí nghiệm B đo độ sâu tìm kiếm đạt được dưới một ngân sách thời gian cố định.
- Thí nghiệm C cho các agent đấu vòng tròn từ nhiều khai cuộc và tổng hợp thắng/thua/hòa cùng số chu kỳ trung bình.
- Khi chạy trực tiếp, script ghi `results_cost.csv`, `results_depth_budget.csv` và `results_matches.csv` vào thư mục làm việc hiện tại.

Lưu ý: tên file hiện có là `tank_experiements.py` (thừa chữ `e` so với `experiments`); khi chạy, dùng đúng tên file này.

### `arena.py`, `agent_loader.py` và `agents/`

> **Thuộc yêu cầu:** ex2 – YC3 (cơ chế nạp thuật toán nhóm khác và cho các thuật toán thi đấu). Phần giao diện PyGame của YC3 nằm ở `tank_gui.py`, hiện đang rỗng.

Các file này bổ sung cách chơi game với agent có sẵn hoặc agent plugin:

- `arena.py` điều khiển một ván người-với-agent hoặc agent-với-agent. Mỗi lượt agent chạy trên bản sao trạng thái trong worker thread; hết thời gian, lỗi hoặc trả sai kiểu hành động thì nước đi được thay bằng `STAY`. Chế độ dòng lệnh có thể đấu hai agent qua nhiều khai cuộc.
- `agent_loader.py` nạp agent từ file `.py`. Plugin có thể cung cấp biến `AGENT`, hàm `create_agent()`, một class có `choose_action`, hoặc hàm `choose_action(state)`; loader kiểm tra agent trước khi dùng.
- `agents/README.md` mô tả API plugin. `greedy_agent.py` là ví dụ chọn bắn khi ngắm trúng, nếu không thì tiến gần căn cứ; `function_agent.py` là ví dụ plugin dạng hàm.
- `tank_gui.py` hiện đang rỗng; giao diện chưa được triển khai trong file này.

Chạy đấu agent từ thư mục `source/ex2`, ví dụ: `python arena.py random hab --games 3`. Có thể thay `random` hoặc `hab` bằng đường dẫn plugin trong `agents/`.

## `ex3`: Kakuro bằng CSP

Kakuro được biểu diễn thành bài toán thỏa mãn ràng buộc (CSP): mỗi ô trắng là một biến có miền chữ số 1-9; mỗi dãy ngang/dọc phải có tổng đúng với gợi ý và không lặp chữ số.

### Các module chính

> **Thuộc yêu cầu:** `kakuro_csp.py` thuộc ex3 – YC1; `kakuro_solver.py` thuộc ex3 – YC1 (kỹ thuật) và YC2 (solver); `kakuro_experiments.py` và `puzzles/complex_9x9.txt` thuộc ex3 – YC2; `kakuro_trace.py` và `kakuro_gui.py` thuộc ex3 – YC3.

- `kakuro_csp.py` đọc lưới từ văn bản, tìm các dãy ràng buộc (`Run`), tạo miền giá trị và quan hệ láng giềng. `KakuroCSP.is_solution` kiểm tra nghiệm; `statistics` thống kê kích thước mô hình.
- `kakuro_solver.py` giải CSP bằng lan truyền ràng buộc và quay lui. Có thể bật/tắt lọc miền, MRV, Degree, LCV; hỗ trợ giới hạn node, khởi động lại ngẫu nhiên và đếm nghiệm. `SolverStats` lưu node, backtrack, revise và thời gian.
- `kakuro_trace.py` nhận sự kiện từ solver qua observer và lưu snapshot miền giá trị trong từng `TraceStep`. Ba preset cho phép so sánh cấu hình đầy đủ, chỉ propagation, hoặc backtracking thuần.
- `kakuro_gui.py` dùng PyGame để xem từng bước giải, tua timeline, xem miền của ô, chuyển preset, nạp puzzle hoặc sinh puzzle mới.
- `generate_puzzle.py` tạo Kakuro từ mẫu ô trắng/đen và sinh lời giải đã biết; `random_pattern` tạo mẫu ngẫu nhiên với các dãy có độ dài hợp lệ.
- `kakuro_experiments.py` chạy kiểm tra tính đúng/duy nhất (A), so sánh kỹ thuật (B), độ ổn định qua nhiều seed (C), và khả năng mở rộng theo kích thước (D). Kết quả được lưu thành `results_ablation.csv`, `results_stability.csv` và `results_scaling.csv` (khi chạy D).

### Dữ liệu và cách chạy

Thư mục `puzzles/` có `demo_6x5.txt`, `demo_backtracking.txt` và `complex_9x9.txt`. Định dạng dùng `.` cho ô trắng, `#` cho ô đen, và `down\\across` cho gợi ý tổng.

Chạy từ thư mục `source/ex3` để đường dẫn puzzle và file kết quả khớp mặc định:

```bash
python kakuro_gui.py
python kakuro_solver.py puzzles/complex_9x9.txt
python kakuro_experiments.py A B C D
```

GUI cần `pygame`; `kakuro_solver.py` và `kakuro_experiments.py` chỉ dùng thư viện chuẩn của Python.

## Quan hệ giữa các file

```text
ex1:
nqueens_cnf.py ──> nqueens_sat.py ──> kiểm tra nghiệm ──> CSV/biểu đồ
nqueens_minconflicts.py ────────────> results_minconflicts.csv

ex2:
tank_game.py ──> tank_ai.py / agent_loader.py ──> arena.py ──> ván đấu
    └────────────────────── tank_experiements.py ──> các file CSV thí nghiệm

ex3:
puzzles/ ──> kakuro_csp.py ──> kakuro_solver.py ──> nghiệm
                      └─> kakuro_trace.py ──> kakuro_gui.py
    kakuro_experiments.py ──> CSV kiểm thử / so sánh
```

Với `ex1`, chạy từ thư mục gốc repo để import module CNF hoạt động; `ex2` và `ex3` nên chạy từ thư mục bài tập để đường dẫn plugin, puzzle và file kết quả khớp mặc định.

```bash
python -m source.ex1.nqueens_sat
python source/ex1/nqueens_minconflicts.py
```

## Tra cứu các hàm

Mỗi dòng nêu công dụng và điểm quan trọng nhất của hàm. Các phương thức khởi tạo (`__init__`) dùng để thiết lập dữ liệu ban đầu cho lớp.

### [ex1/nqueens_cnf.py](source/ex1/nqueens_cnf.py)

| Hàm | Công dụng và điểm cần nhớ |
|---|---|
| `Board.__init__` | Tạo bàn cờ kích thước `N`; từ chối `N < 1`. |
| `Board.var` | Đổi tọa độ ô thành ID biến SAT, bắt đầu từ 1. |
| `Board.square` | Đổi ID biến SAT ngược thành tọa độ ô. |
| `Board.num_vars` | Trả về tổng số biến, bằng `N x N`. |
| `Board.squares` | Liệt kê toàn bộ ô trên bàn cờ. |
| `Board.model_to_queens` | Lấy các biến dương trong mô hình SAT và đổi thành vị trí hậu. |
| `Board.render` | In lời giải thành bàn cờ, `Q` là hậu và `.` là ô trống. |
| `CNFFormula.__init__` | Tạo danh sách rỗng để lưu các mệnh đề. |
| `CNFFormula.add` | Thêm một mệnh đề vào công thức CNF. |
| `CNFFormula.__len__` | Trả về số mệnh đề hiện có. |
| `CNFFormula.__iter__` | Cho phép duyệt lần lượt các mệnh đề. |
| `CNFFormula.to_dimacs` | Xuất CNF theo DIMACS để dùng với SAT solver. |
| `ConstraintGenerator.__init__` | Gắn bộ sinh ràng buộc với bàn cờ cần xét. |
| `ConstraintGenerator.attacks` | Kiểm tra hai ô khác nhau có cùng hàng, cột hoặc đường chéo không. |
| `ConstraintGenerator.attacking_pairs_naive` | Tìm cặp ô tấn công bằng cách kiểm tra mọi cặp; đơn giản nhưng chậm hơn. |
| `ConstraintGenerator.attacking_pairs_grouped` | Gom ô theo hàng, cột và đường chéo để tạo cặp tấn công hiệu quả hơn. |
| `ConstraintGenerator.at_least_one_per_row` | Tạo mệnh đề yêu cầu mỗi hàng có ít nhất một hậu. |
| `ConstraintGenerator.at_most_one_clauses` | Tạo mệnh đề cấm đặt hậu đồng thời ở hai ô tấn công nhau. |
| `ConstraintGenerator.generate` | Kết hợp các ràng buộc thành CNF; mặc định dùng cách gom nhóm tối ưu. |
| `ConstraintGenerator.expected_clause_count` | Tính số mệnh đề dự kiến để đối chiếu kết quả sinh CNF. |

### [ex1/nqueens_sat.py](source/ex1/nqueens_sat.py)

| Hàm | Công dụng và điểm cần nhớ |
|---|---|
| `SATQueensSolver.__init__` | Chuẩn bị bàn cờ, bộ sinh CNF và các biến ghi thời gian. |
| `SATQueensSolver.build` | Sinh CNF và đo riêng thời gian tạo công thức. |
| `SATQueensSolver.solve` | Dùng Glucose3 tìm lời giải; tự gọi `build` nếu CNF chưa có, trả `None` nếu vô nghiệm. |
| `SATQueensSolver.is_valid` | Kiểm tra độc lập số lượng hậu và các cặp xung đột trong lời giải. |
| `ExperimentRunner.__init__` | Lưu các kích thước bàn cờ cần chạy và nơi tích lũy kết quả. |
| `ExperimentRunner.run` | Chạy solver cho từng kích thước, ghi số biến, số mệnh đề, thời gian và tính hợp lệ. |
| `ExperimentRunner.save_csv` | Ghi kết quả thí nghiệm ra CSV. |
| `ExperimentRunner.plot` | Vẽ đồ thị kích thước CNF và thời gian chạy; cần `matplotlib`. |

### [ex1/nqueens_minconflicts.py](source/ex1/nqueens_minconflicts.py)

| Hàm | Công dụng và điểm cần nhớ |
|---|---|
| `QueensState.__init__` | Tạo trạng thái và các bộ đếm hậu theo hàng, đường chéo để tính nhanh xung đột. |
| `QueensState._add` | Cập nhật các bộ đếm khi thêm hoặc bỏ một hậu. |
| `QueensState.conflicts` | Đếm số hậu xung đột nếu một hậu ở cột, hàng chỉ định; loại phần đóng góp của chính nó. |
| `QueensState.move` | Chuyển hậu trong một cột và cập nhật bộ đếm tương ứng. |
| `QueensState.conflicted_columns` | Trả về các cột có hậu đang bị xung đột. |
| `QueensState.total_conflicts` | Tính tổng số cặp xung đột trên bàn cờ. |
| `VariableSelector.reset` | Đặt lại trạng thái của bộ chọn trước mỗi lần giải; lớp gốc không làm gì. |
| `VariableSelector.select` | Giao diện để lớp con chọn cột xung đột cần sửa. |
| `RandomSelector.select` | Chọn ngẫu nhiên một cột đang xung đột. |
| `MaxConflictSelector.select` | Chọn cột có nhiều xung đột nhất; chọn ngẫu nhiên nếu hòa. |
| `MaxConflictTabuSelector.__init__` | Đặt thời gian cấm chọn lại một cột vừa sửa (tabu tenure). |
| `MaxConflictTabuSelector.reset` | Xóa lịch sử tabu và đặt lại số bước cho lần chạy mới. |
| `MaxConflictTabuSelector.select` | Chọn cột xung đột lớn nhất chưa bị cấm; dùng các cột xung đột làm dự phòng nếu cần. |
| `MinConflictsSolver.__init__` | Thiết lập kích thước, bộ chọn, giới hạn bước và bộ sinh số ngẫu nhiên. |
| `MinConflictsSolver.random_initial` | Tạo trạng thái ban đầu với một hậu ngẫu nhiên trong mỗi cột. |
| `MinConflictsSolver.best_value` | Chọn hàng có ít xung đột nhất cho hậu ở cột đã chọn; hòa thì chọn ngẫu nhiên. |
| `MinConflictsSolver.solve` | Lặp việc chọn cột và chuyển hậu đến khi hết xung đột hoặc chạm giới hạn bước. |
| `Experiment.__init__` | Thiết lập kích thước, số lần thử và các bộ chọn cần so sánh. |
| `Experiment.run` | Chạy nhiều lần cho từng cấu hình, tính tỷ lệ thành công, số bước và thời gian trung bình. |
| `Experiment.save_csv` | Lưu bảng kết quả Min-Conflicts ra CSV. |

### [ex2/tank_game.py](source/ex2/tank_game.py)

| Hàm | Công dụng và điểm cần nhớ |
|---|---|
| `GameConfig.__init__` | Thiết lập kích thước bàn, tường, vị trí xe tăng và căn cứ; có giá trị mặc định. |
| `GameConfig._default_walls` | Tạo bố cục tường đối xứng để hai bên có điều kiện công bằng. |
| `GameState.__init__` | Lưu bản đồ, đơn vị, đạn, người chơi tới lượt và số chu kỳ. |
| `GameState.initial` | Tạo trạng thái bắt đầu từ cấu hình, hoặc dùng bản đồ mặc định. |
| `GameState.copy` | Sao chép trạng thái cùng các đối tượng game để nước đi không sửa trạng thái cũ. |
| `GameState.in_bounds` | Kiểm tra tọa độ có nằm trong bàn cờ không. |
| `GameState.is_free` | Kiểm tra ô có thể cho xe tăng đi vào: trong bàn, không có tường, xe tăng hay căn cứ. |
| `GameState.has_bullet_in_flight` | Kiểm tra người chơi đã có đạn đang bay chưa. |
| `GameState.legal_actions` | Liệt kê hành động hợp lệ; luôn có `STAY`, và chỉ cho bắn khi chưa có đạn bay. |
| `GameState.apply` | Áp dụng hành động lên bản sao; sau lượt MIN thì cập nhật đạn và tăng chu kỳ. |
| `GameState._move_bullets` | Di chuyển đạn tối đa 3 ô, xử lý va chạm và sát thương rồi loại đạn đã trúng. |
| `GameState._destroyed` | Kiểm tra xe tăng hoặc căn cứ của một bên đã hết HP chưa. |
| `GameState.is_terminal` | Kiểm tra game kết thúc sau một chu kỳ, khi có bên bị hạ hoặc hết giới hạn chu kỳ. |
| `GameState.utility` | Tính điểm kết quả từ góc nhìn MAX; thắng sớm có điểm cao hơn, hòa bằng 0. |
| `GameState.key` | Tạo biểu diễn có thể băm của trạng thái để nhận diện trạng thái trùng. |
| `GameState.render` | Chuyển trạng thái thành bàn cờ ASCII kèm HP và số chu kỳ. |

### [ex2/tank_ai.py](source/ex2/tank_ai.py)

| Hàm | Công dụng và điểm cần nhớ |
|---|---|
| `first_hit` | Tìm vật thể đầu tiên trên đường bắn; trả về `None` nếu đạn đi ra ngoài bàn. |
| `HeuristicEvaluator.__init__` | Thiết lập trọng số chấm điểm, cho phép thay một số trọng số mặc định. |
| `HeuristicEvaluator._aim` | Ước lượng khả năng ngắm trúng xe tăng hoặc căn cứ đối phương. |
| `HeuristicEvaluator.evaluate` | Chấm trạng thái theo chênh lệch HP, khả năng bắn, đạn đang bay và khoảng cách; giới hạn điểm trong khoảng `-900..900`. |
| `Searcher.__init__` | Thiết lập độ sâu, cắt tỉa Alpha-Beta, heuristic và bộ thống kê. |
| `Searcher.ordered_actions` | Sắp thứ tự hành động để tìm nước bắn/tiến gần mục tiêu sớm; hàm phụ `key` xếp hạng từng nước. |
| `Searcher._value` | Tìm điểm Minimax đệ quy; có thể dừng theo thời hạn và cắt nhánh khi Alpha-Beta bật. |
| `Searcher._root` | Duyệt các nước đi đầu tiên để chọn hành động có giá trị tốt nhất. |
| `Searcher.search` | Chạy tìm kiếm và trả hành động cùng thống kê; có giới hạn thời gian thì dùng iterative deepening. |
| `Agent.choose_action` | Giao diện bắt buộc cho agent chọn nước đi theo lượt hiện tại. |
| `RandomAgent.__init__` | Tạo bộ sinh số ngẫu nhiên, có thể cố định seed. |
| `RandomAgent.choose_action` | Chọn ngẫu nhiên một nước hợp lệ. |
| `SearchAgent.__init__` | Tạo searcher theo một trong bốn cấu hình, độ sâu và giới hạn thời gian. |
| `SearchAgent.choose_action` | Tìm nước đi bằng searcher và lưu thống kê của lần tìm gần nhất. |

### [ex2/tank_experiements.py](source/ex2/tank_experiements.py)

| Hàm | Công dụng và điểm cần nhớ |
|---|---|
| `make_scenarios` | Tạo trạng thái ban đầu và các trạng thái giữa trận có thể tái lập bằng seed. |
| `write_csv` | Ghi danh sách kết quả ra CSV; không tạo file nếu danh sách rỗng. |
| `experiment_cost` | So sánh số node, thời gian và lần cắt nhánh giữa các cấu hình; kiểm tra Alpha-Beta cho cùng kết quả với Minimax. |
| `experiment_depth_budget` | Đo độ sâu tìm kiếm đạt được dưới các ngân sách thời gian khác nhau. |
| `play_match` | Chạy một ván giữa hai agent, trả kết quả thắng/thua/hòa và số chu kỳ. |
| `openings` | Tạo các thế khai cuộc ngẫu nhiên ngắn để dùng khi đấu thử. |
| `experiment_matches` | Cho các cấu hình đấu vòng tròn từ nhiều khai cuộc và tổng hợp kết quả. |

### API các file mới của `ex2`

| File / hàm chính | Công dụng và điểm cần nhớ |
|---|---|
| `arena.py: GameController.update` | Chạy agent nền và áp dụng kết quả khi sẵn sàng; timeout, lỗi hoặc hành động sai đều thành `STAY`. |
| `arena.py: GameController.submit_human_action` | Nhận nước đi nếu đúng lượt và đúng kiểu `Action`. |
| `arena.py: run_match` | Chạy ván không giao diện đến khi kết thúc hoặc đạt giới hạn chu kỳ. |
| `arena.py: random_openings`, `head_to_head` | Tạo khai cuộc và đấu hai agent, đổi bên rồi tổng hợp thống kê. |
| `agent_loader.py: load_agent_from_file` | Nạp plugin theo một trong bốn kiểu API và chạy thử để xác thực. |
| `agent_loader.py: discover_agent_files` | Tìm plugin `.py` trong `agents/`, bỏ qua tên bắt đầu bằng `_`. |
| `agent_loader.py: builtin_specs`, `file_spec`, `all_specs` | Tạo danh sách agent có sẵn và plugin cho menu chọn người chơi. |
| `agents/greedy_agent.py: GreedyAgent.choose_action` | Bắn nếu ngắm trúng mục tiêu; nếu không thì chọn bước tiến gần căn cứ địch. |
| `agents/function_agent.py: choose_action` | Ví dụ plugin dạng hàm, chọn nước hợp lệ và đôi khi ưu tiên bắn. |

### API chính của `ex3`

| File / hàm chính | Công dụng và điểm cần nhớ |
|---|---|
| `kakuro_csp.py: KakuroPuzzle.from_text` | Đọc lưới và kiểm tra cú pháp clue. |
| `kakuro_csp.py: KakuroPuzzle._extract_runs` | Tạo các dãy ngang/dọc có ràng buộc tổng từ clue. |
| `kakuro_csp.py: Run.combos`, `Run.consistent` | Sinh tổ hợp số đúng tổng và kiểm tra không lặp/tổng còn khả thi. |
| `kakuro_csp.py: KakuroCSP.__init__` | Tạo biến, miền, runs-of và láng giềng; có thể lọc miền ban đầu. |
| `kakuro_csp.py: KakuroCSP.is_solution`, `statistics` | Xác nhận nghiệm và thống kê kích thước CSP. |
| `kakuro_solver.py: KakuroSolver._propagate` | Lọc ràng buộc đến khi ổn định hoặc phát hiện mâu thuẫn. |
| `kakuro_solver.py: KakuroSolver._select`, `_order_values` | Chọn biến theo MRV/Degree và giá trị theo LCV nếu bật. |
| `kakuro_solver.py: KakuroSolver.solve` | Tìm một nghiệm, tôn trọng giới hạn node và lưu thống kê. |
| `kakuro_solver.py: KakuroSolver.solve_with_restarts` | Thử lại với seed mới và giới hạn node tăng dần. |
| `kakuro_solver.py: KakuroSolver.count_solutions` | Đếm tối đa `limit` nghiệm; dừng ở 2 thường đủ kiểm tra tính duy nhất. |
| `kakuro_trace.py: TraceRecorder.observe` | Chuyển sự kiện solver thành bước trace kèm snapshot miền và trạng thái gán. |
| `kakuro_trace.py: build_trace` | Tạo CSP, recorder và solver; trả chuỗi bước để GUI phát lại. |
| `generate_puzzle.py: generate` | Sinh puzzle cùng lời giải đã biết từ mẫu ô trắng/đen. |
| `generate_puzzle.py: random_pattern` | Tạo mẫu ngẫu nhiên và sửa dãy có độ dài không hợp lệ. |
| `kakuro_experiments.py: verify_independent` | Kiểm tra nghiệm trực tiếp từ văn bản puzzle, không dựa vào lớp CSP. |
| `kakuro_experiments.py: experiment_correctness` | Kiểm tra nghiệm, tính duy nhất và kết quả giữa các cấu hình. |
| `kakuro_experiments.py: experiment_ablation`, `experiment_stability`, `experiment_scaling` | So sánh kỹ thuật, độ ổn định theo seed và khả năng giải puzzle lớn hơn. |
| `kakuro_gui.py: KakuroApp.handle`, `update`, `draw` | Xử lý thao tác, cập nhật phát lại và vẽ giao diện. |
| `kakuro_gui.py: main` | Nạp puzzle và chạy vòng lặp PyGame. |

### Dữ liệu kết quả và file chưa triển khai

Các file `.csv` trong `ex1`, `ex2` và `ex3` là kết quả đã lưu, không phải đầu vào solver tự đọc. `source/ex2/tank_gui.py` hiện để trống; phần điều khiển agent và đấu giải nằm trong `arena.py`.