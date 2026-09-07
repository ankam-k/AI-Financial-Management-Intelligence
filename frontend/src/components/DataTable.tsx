/** The table view every chart carries. */

export interface Column<T> {
  key: string;
  header: string;
  numeric?: boolean;
  render: (row: T) => string;
}

export function DataTable<T>({
  caption,
  columns,
  rows,
}: {
  caption: string;
  columns: Column<T>[];
  rows: T[];
}) {
  return (
    <div className="table-scroll">
      <table className="data-table">
        <caption>{caption}</caption>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key} scope="col" className={column.numeric ? 'numeric' : undefined}>
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {columns.map((column) => (
                <td key={column.key} className={column.numeric ? 'numeric' : undefined}>
                  {column.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
