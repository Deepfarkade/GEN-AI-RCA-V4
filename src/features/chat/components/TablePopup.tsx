import React from 'react';

interface TablePopupProps {
  tableData: {
    columns: string[];
    records: Record<string, any>[];
  };
  onClose: () => void;
}

const TablePopup: React.FC<TablePopupProps> = ({ tableData, onClose }) => {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50">
      <div className="bg-white rounded-lg shadow-lg max-w-3xl w-full max-h-[80vh] overflow-auto p-6">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-500 hover:text-gray-700"
        >
          &#x2715;
        </button>
        {/* Table Display */}
        <div className="overflow-auto max-h-96 scrollbar">
          <table className="table-auto border-collapse border border-gray-300 w-full text-sm">
            <thead>
              <tr>
                {tableData.columns.map((column, index) => (
                  <th
                    key={index}
                    className="border border-gray-300 px-4 py-2 bg-primary text-center text-black"
                  >
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tableData.records.map((record, rowIndex) => (
                <tr key={rowIndex}>
                  {tableData.columns.map((column, colIndex) => (
                    <td
                      key={colIndex}
                      className="border border-gray-300 px-4 py-2 text-left"
                    >
                      {record[column]}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default TablePopup;
