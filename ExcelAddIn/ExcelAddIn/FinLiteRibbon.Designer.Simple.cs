namespace ExcelAddIn
{
    partial class FinLiteRibbon : Microsoft.Office.Tools.Ribbon.RibbonBase
    {
        /// <summary>
        /// Required designer variable.
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        public FinLiteRibbon()
            : base(Globals.Factory.GetRibbonFactory())
        {
            InitializeComponent();
        }

        /// <summary> 
        /// Clean up any resources being used.
        /// </summary>
        /// <param name="disposing">true if managed resources should be disposed; otherwise, false.</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Component Designer generated code

        /// <summary>
        /// Required method for Designer support - do not modify
        /// the contents of this method with the code editor.
        /// </summary>
        private void InitializeComponent()
        {
            this.finAnalysisTab = this.Factory.CreateRibbonTab();
            this.financialGroup = this.Factory.CreateRibbonGroup();
            this.finLiteButton = this.Factory.CreateRibbonButton();
            this.finAnalysisTab.SuspendLayout();
            this.financialGroup.SuspendLayout();
            this.SuspendLayout();
            // 
            // finAnalysisTab
            // 
            this.finAnalysisTab.ControlId.ControlIdType = Microsoft.Office.Tools.Ribbon.RibbonControlIdType.Office;
            this.finAnalysisTab.Groups.Add(this.financialGroup);
            this.finAnalysisTab.Label = "FinLite";
            this.finAnalysisTab.Name = "finAnalysisTab";
            // 
            // financialGroup
            // 
            this.financialGroup.Items.Add(this.finLiteButton);
            this.financialGroup.Label = "Financial Analysis";
            this.financialGroup.Name = "financialGroup";
            // 
            // finLiteButton
            // 
            this.finLiteButton.ControlSize = Microsoft.Office.Core.RibbonControlSize.RibbonControlSizeLarge;
            this.finLiteButton.Label = "FinLite";
            this.finLiteButton.Name = "finLiteButton";
            this.finLiteButton.ScreenTip = "Toggle FinLite Panel";
            this.finLiteButton.SuperTip = "Click to show or hide the FinLite financial analysis panel";
            this.finLiteButton.Click += new Microsoft.Office.Tools.Ribbon.RibbonControlEventHandler(this.FinLiteButton_Click);
            // 
            // FinLiteRibbon
            // 
            this.Name = "FinLiteRibbon";
            this.RibbonType = "Microsoft.Excel.Workbook";
            this.Tabs.Add(this.finAnalysisTab);
            this.Load += new Microsoft.Office.Tools.Ribbon.RibbonUIEventHandler(this.FinLiteRibbon_Load);
            this.finAnalysisTab.ResumeLayout(false);
            this.finAnalysisTab.PerformLayout();
            this.financialGroup.ResumeLayout(false);
            this.financialGroup.PerformLayout();
            this.ResumeLayout(false);

        }

        #endregion

        internal Microsoft.Office.Tools.Ribbon.RibbonTab finAnalysisTab;
        internal Microsoft.Office.Tools.Ribbon.RibbonGroup financialGroup;
        internal Microsoft.Office.Tools.Ribbon.RibbonButton finLiteButton;
    }
}
