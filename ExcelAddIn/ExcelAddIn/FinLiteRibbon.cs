using System;
using Microsoft.Office.Tools.Ribbon;
using System.Windows.Forms;

namespace ExcelAddIn
{
    public partial class FinLiteRibbon
    {
        private void FinLiteRibbon_Load(object sender, RibbonUIEventArgs e)
        {
        }

        private void FinLiteButton_Click(object sender, RibbonControlEventArgs e)
        {
            try
            {
                var addIn = Globals.ThisAddIn;
                if (addIn?.TaskPane != null)
                {
                    addIn.TaskPane.Visible = !addIn.TaskPane.Visible;
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error toggling FinLite pane: {ex.Message}", "FinLite Error", 
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }
    }
}
