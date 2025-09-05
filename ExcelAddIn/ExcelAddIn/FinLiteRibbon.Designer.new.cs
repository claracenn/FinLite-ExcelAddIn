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
            this.showHideFinLiteButton = this.Factory.CreateRibbonButton();
            this.analyzeSelectionButton = this.Factory.CreateRibbonButton();
            this.startBackendButton = this.Factory.CreateRibbonButton();
            this.settingsButton = this.Factory.CreateRibbonButton();
            this.helpButton = this.Factory.CreateRibbonButton();
            this.finAnalysisTab.SuspendLayout();
            this.financialGroup.SuspendLayout();
            this.SuspendLayout();
            // 
            // finAnalysisTab
            // 
            this.finAnalysisTab.ControlId.ControlIdType = Microsoft.Office.Tools.Ribbon.RibbonControlIdType.Office;
            this.finAnalysisTab.Groups.Add(this.financialGroup);
            this.finAnalysisTab.Label = "Financial Analysis";
            this.finAnalysisTab.Name = "finAnalysisTab";
            // 
            // financialGroup
            // 
            this.financialGroup.Items.Add(this.showHideFinLiteButton);
            this.financialGroup.Items.Add(this.analyzeSelectionButton);
            this.financialGroup.Items.Add(this.startBackendButton);
            this.financialGroup.Items.Add(this.settingsButton);
            this.financialGroup.Items.Add(this.helpButton);
            this.financialGroup.Label = "FinLite Tools";
            this.financialGroup.Name = "financialGroup";
            // 
            // showHideFinLiteButton
            // 
            this.showHideFinLiteButton.ControlSize = Microsoft.Office.Core.RibbonControlSize.RibbonControlSizeLarge;
            this.showHideFinLiteButton.Image = global::ExcelAddIn.Properties.Resources.finlite_icon;
            this.showHideFinLiteButton.Label = "Show/Hide FinLite";
            this.showHideFinLiteButton.Name = "showHideFinLiteButton";
            this.showHideFinLiteButton.ShowImage = true;
            this.showHideFinLiteButton.Click += new Microsoft.Office.Tools.Ribbon.RibbonControlEventHandler(this.ShowHideFinLiteButton_Click);
            // 
            // analyzeSelectionButton
            // 
            this.analyzeSelectionButton.Image = global::ExcelAddIn.Properties.Resources.analyze_icon;
            this.analyzeSelectionButton.Label = "Analyze Selection";
            this.analyzeSelectionButton.Name = "analyzeSelectionButton";
            this.analyzeSelectionButton.ShowImage = true;
            this.analyzeSelectionButton.Click += new Microsoft.Office.Tools.Ribbon.RibbonControlEventHandler(this.AnalyzeSelectionButton_Click);
            // 
            // startBackendButton
            // 
            this.startBackendButton.Image = global::ExcelAddIn.Properties.Resources.backend_icon;
            this.startBackendButton.Label = "Start Backend";
            this.startBackendButton.Name = "startBackendButton";
            this.startBackendButton.ShowImage = true;
            this.startBackendButton.Click += new Microsoft.Office.Tools.Ribbon.RibbonControlEventHandler(this.StartBackendButton_Click);
            // 
            // settingsButton
            // 
            this.settingsButton.Image = global::ExcelAddIn.Properties.Resources.settings_icon;
            this.settingsButton.Label = "Settings";
            this.settingsButton.Name = "settingsButton";
            this.settingsButton.ShowImage = true;
            this.settingsButton.Click += new Microsoft.Office.Tools.Ribbon.RibbonControlEventHandler(this.SettingsButton_Click);
            // 
            // helpButton
            // 
            this.helpButton.Image = global::ExcelAddIn.Properties.Resources.help_icon;
            this.helpButton.Label = "Help";
            this.helpButton.Name = "helpButton";
            this.helpButton.ShowImage = true;
            this.helpButton.Click += new Microsoft.Office.Tools.Ribbon.RibbonControlEventHandler(this.HelpButton_Click);
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
        internal Microsoft.Office.Tools.Ribbon.RibbonButton showHideFinLiteButton;
        internal Microsoft.Office.Tools.Ribbon.RibbonButton analyzeSelectionButton;
        internal Microsoft.Office.Tools.Ribbon.RibbonButton startBackendButton;
        internal Microsoft.Office.Tools.Ribbon.RibbonButton settingsButton;
        internal Microsoft.Office.Tools.Ribbon.RibbonButton helpButton;
    }
}
